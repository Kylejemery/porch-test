"""The Porch Test: an Inspect task.

Run one model on the public items, with a judge model for rubric scoring:

    inspect eval porch_test/task.py --model anthropic/<model> --model-role grader=openai/<model>

Run a single track:

    inspect eval porch_test/task.py -T track=stoic_logic --model ... --model-role grader=...

Scoring follows RUBRIC_SPEC.md: the judge scores each criterion 0, 1 or 2 and
extracts the fields an item's `exact` block names; code compares those fields.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import get_model
from inspect_ai.scorer import (
    Metric,
    SampleScore,
    Score,
    Target,
    grouped,
    mean,
    metric,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState, generate

ITEMS_DIR = Path(__file__).resolve().parent.parent / "items"

TRACKS = [
    "stoic_logic",
    "sophisms",
    "doctrine",
    "applied_ethics",
    "epistemic_honesty",
]


def load_items(track: str | None = None, include_unverified: bool = True) -> list[dict[str, Any]]:
    """Load every item file. By default drafts with unverified sources are
    included (useful while building); pass include_unverified=False for a
    publishable run."""
    items: list[dict[str, Any]] = []
    for path in sorted(ITEMS_DIR.glob("track*.json")):
        items.extend(json.loads(path.read_text(encoding="utf-8")))
    items = [i for i in items if i.get("status") not in ("held", "retired")]
    if track:
        items = [i for i in items if i["track"] == track]
    if not include_unverified:
        items = [
            i for i in items
            if all(s["status"] != "to_verify" for s in i.get("sources", []))
        ]
    return items


def to_sample(item: dict[str, Any]) -> Sample:
    return Sample(
        id=item["id"],
        input=item["prompt"],
        target=item["gold_answer"],
        metadata={
            "track": item["track"],
            "rubric": item["rubric"],
            "exact": item.get("exact"),
            "difficulty": item.get("difficulty"),
        },
    )


JUDGE_TEMPLATE = """You are grading an answer to a question about Stoic philosophy.
You will score the answer against a rubric. Be strict and literal.

QUESTION:
{question}

REFERENCE ANSWER (full marks):
{gold}

RUBRIC (score each criterion):
{rubric}

Scale for each criterion:
2 = met clearly
1 = partly met, or met with a minor error
0 = missing, wrong, or contradicted elsewhere in the answer
Score the answer's final position. A clearly marked self-correction (where the
answer flags an earlier statement as mistaken and settles on a different final
position) is not a contradiction. Leaving the matter unresolved, or asserting
both sides without settling, is a contradiction and scores 0 on any affected
criterion.
Do not reward length, tone or formatting.

{exact_block}ANSWER TO GRADE:
{answer}

Respond with JSON only, in this shape:
{{"criteria": [{{"n": 1, "score": 0, "reason": "one sentence"}}, ...]{exact_shape}}}
"""

EXACT_BLOCK = """Also extract what the answer commits to for these fields. Each
field must take exactly one allowed value, from this list; use null if the
answer does not commit to a value. Do not invent new values.
{fields}

"""

EXACT_FIELD_SPECS: dict[str, str] = {
    "indemonstrable": "one of 1, 2, 3, 4, 5, or null",
    "verdict": 'exactly one of "valid", "invalid", or "valid_nonsyllogistic"',
    "attested": 'exactly one of true, false, "paraphrase", or "loose_translation"',
    "locator": 'a short string such as "Med. 3.9"',
    "analysis": "a list of indemonstrable numbers in order, for example [2, 3]",
}


def _normalize(v: Any) -> Any:
    """Normalize case and whitespace for comparison. Strings are lowercased and
    their internal whitespace is collapsed. Lists and dicts recurse."""
    if isinstance(v, str):
        return " ".join(v.strip().split()).lower()
    if isinstance(v, list):
        return [_normalize(x) for x in v]
    if isinstance(v, dict):
        return {k: _normalize(val) for k, val in v.items()}
    return v


def build_judge_prompt(state: TaskState, target: Target) -> str:
    md = state.metadata
    rubric = "\n".join(f"{n}. {c}" for n, c in enumerate(md["rubric"], start=1))
    exact = md.get("exact")
    if exact:
        lines: list[str] = []
        for k, v in exact.items():
            spec = EXACT_FIELD_SPECS.get(k)
            if spec is None:
                lines.append(f"- {k}: example value {json.dumps(v)}")
            else:
                lines.append(f"- {k}: {spec}")
        fields = "\n".join(lines)
        exact_block = EXACT_BLOCK.format(fields=fields)
        exact_shape = ', "extracted": {' + ", ".join(f'"{k}": ...' for k in exact) + "}"
    else:
        exact_block = ""
        exact_shape = ""
    return JUDGE_TEMPLATE.format(
        question=state.input_text,
        gold=target.text,
        rubric=rubric,
        exact_block=exact_block,
        answer=state.output.completion,
        exact_shape=exact_shape,
    )


def parse_judge(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


JUDGE_ATTEMPTS = 2


def check_judge(parsed: dict[str, Any] | None, n: int) -> tuple[dict[int, int] | None, str]:
    """Criterion scores from a parsed judge response, or None and the reason
    the response cannot be used."""
    if not parsed or "criteria" not in parsed:
        return None, "Judge output could not be parsed."
    try:
        scores = {
            int(c["n"]): int(c["score"])
            for c in parsed["criteria"]
            if isinstance(c, dict) and "n" in c and "score" in c
        }
    except (TypeError, ValueError):
        return None, "Judge criterion id or score was not an integer."
    if set(scores.keys()) != set(range(1, n + 1)):
        return None, f"Judge returned criterion ids {sorted(scores.keys())} but rubric has 1..{n}."
    return scores, ""


@scorer(metrics=[grouped(mean(), "track", all="groups"), grouped(stderr(), "track", all=False, name_template="{group_name}_stderr")])
def rubric_judge(judge: str | None = None):
    """Rubric scoring by a judge model, plus code comparison of exact fields.

    A judge response that cannot be used is retried once. If the retry fails
    too, the sample is recorded as unscored: it keeps the raw responses but is
    left out of every mean (Inspect skips NaN scores), and `judge_unscored`
    counts it."""

    async def score(state: TaskState, target: Target) -> Score:
        grader = get_model(judge) if judge else get_model(role="grader", required=True)
        n = len(state.metadata["rubric"])
        prompt = build_judge_prompt(state, target)
        failures: list[dict[str, str]] = []
        for _ in range(JUDGE_ATTEMPTS):
            result = await grader.generate(prompt)
            parsed = parse_judge(result.completion)
            scores, problem = check_judge(parsed, n)
            if scores is not None:
                break
            failures.append({"problem": problem, "judge_raw": result.completion})
        else:
            return Score.unscored(
                reason="judge_parse_failed",
                answer=state.output.completion,
                explanation=f"Judge output unusable on {JUDGE_ATTEMPTS} attempts: "
                            + " / ".join(f["problem"] for f in failures),
                metadata={"parse_failed": True, "unscored": True, "judge_failures": failures},
            )

        points = sum(max(0, min(2, scores[i])) for i in range(1, n + 1))
        value = points / (2 * n)

        exact = state.metadata.get("exact")
        exact_match = None
        if exact:
            extracted = parsed.get("extracted", {}) or {}
            exact_match = {
                k: _normalize(extracted.get(k)) == _normalize(v) for k, v in exact.items()
            }

        explanation = "\n".join(
            f"{c.get('n')}: {c.get('score')} - {c.get('reason', '')}" for c in parsed["criteria"]
        )
        return Score(
            value=value,
            answer=state.output.completion,
            explanation=explanation,
            metadata={
                "criteria": parsed["criteria"],
                "exact_match": exact_match,
                "extracted": parsed.get("extracted"),
                **({"judge_failures": failures} if failures else {}),
            },
        )

    return score


@metric
def count() -> Metric:
    """Sum of the per-sample values (here, the number of unscored samples)."""

    def metric(scores: list[SampleScore]) -> float:
        return float(sum(s.score.as_float() for s in scores))

    return metric


@scorer(metrics=[count()])
def judge_unscored():
    """1 for a sample rubric_judge left unscored, else 0, so the eval summary
    shows how many samples are missing from the means. Runs after rubric_judge."""

    async def score(state: TaskState, target: Target) -> Score:
        judged = state.scores.get("rubric_judge") if state.scores else None
        missing = judged is None or (isinstance(judged.value, float) and math.isnan(judged.value))
        return Score(value=1.0 if missing else 0.0)

    return score


@task
def porch_test(track: str | None = None, verified_only: bool = False, judge: str | None = None):
    if track and track not in TRACKS:
        raise ValueError(f"track must be one of {TRACKS}")
    items = load_items(track=track, include_unverified=not verified_only)
    return Task(
        dataset=MemoryDataset([to_sample(i) for i in items], name="porch_test"),
        solver=[generate()],
        scorer=[rubric_judge(judge=judge), judge_unscored()],
    )
