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
import re
from pathlib import Path
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import get_model
from inspect_ai.scorer import (
    Score,
    Target,
    grouped,
    mean,
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


@scorer(metrics=[grouped(mean(), "track", all="groups"), grouped(stderr(), "track", all=False, name_template="{group_name}_stderr")])
def rubric_judge(judge: str | None = None):
    """Rubric scoring by a judge model, plus code comparison of exact fields."""

    async def score(state: TaskState, target: Target) -> Score:
        grader = get_model(judge) if judge else get_model(role="grader", required=True)
        result = await grader.generate(build_judge_prompt(state, target))
        parsed = parse_judge(result.completion)
        n = len(state.metadata["rubric"])

        if not parsed or "criteria" not in parsed:
            return Score(
                value=0.0,
                answer=state.output.completion,
                explanation="Judge output could not be parsed; rescore this sample.",
                metadata={"judge_raw": result.completion, "parse_failed": True},
            )

        try:
            scores = {
                int(c["n"]): int(c["score"])
                for c in parsed["criteria"]
                if isinstance(c, dict) and "n" in c and "score" in c
            }
        except (TypeError, ValueError):
            return Score(
                value=0.0,
                answer=state.output.completion,
                explanation="Judge criterion id or score was not an integer; rescore this sample.",
                metadata={"judge_raw": result.completion, "parse_failed": True},
            )

        if set(scores.keys()) != set(range(1, n + 1)):
            got = sorted(scores.keys())
            return Score(
                value=0.0,
                answer=state.output.completion,
                explanation=(
                    f"Judge returned criterion ids {got} but rubric has 1..{n}; "
                    "rescore this sample."
                ),
                metadata={
                    "judge_raw": result.completion,
                    "parse_failed": True,
                    "criteria": parsed.get("criteria"),
                },
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
            },
        )

    return score


@task
def porch_test(track: str | None = None, verified_only: bool = False, judge: str | None = None):
    if track and track not in TRACKS:
        raise ValueError(f"track must be one of {TRACKS}")
    items = load_items(track=track, include_unverified=not verified_only)
    return Task(
        dataset=MemoryDataset([to_sample(i) for i in items], name="porch_test"),
        solver=[generate()],
        scorer=rubric_judge(judge=judge),
    )
