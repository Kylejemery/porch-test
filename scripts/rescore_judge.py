"""Rerun the judge on samples whose judge output could not be used.

    py -3.14 scripts/rescore_judge.py logs/<run>.eval

Finds every sample the judge left unparsed or unscored, reruns the same judge
model (the log's grader role) on the stored answer with the current scorer
(one retry, then unscored), and writes a copy of the log with those scores
edited and the metrics recomputed, as logs/<run>_rescored.eval. The model
under test is not called again, and the original log is left untouched.
"""

from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv  # noqa: E402
from inspect_ai.log import ProvenanceData, edit_score, read_eval_log, recompute_metrics, write_eval_log  # noqa: E402
from inspect_ai.scorer import ScoreEdit, Target  # noqa: E402

from calibration import is_unscored  # noqa: E402
from porch_test.task import rubric_judge  # noqa: E402


async def rescore(path: Path) -> None:
    log = read_eval_log(str(path))
    judge = log.eval.model_roles["grader"].model
    score_fn = rubric_judge(judge=judge)
    todo = [s for s in log.samples or [] if is_unscored(s)]
    print(f"{log.eval.model} judged by {judge}: {len(todo)} samples to rescore")

    async def one(s):
        state = SimpleNamespace(
            metadata=s.metadata, input_text=s.input,
            output=SimpleNamespace(completion=s.output.completion),
        )
        return s, await score_fn(state, Target(s.target))

    results = await asyncio.gather(*(one(s) for s in todo))
    for s, new in results:
        old = s.scores["rubric_judge"]
        unscored = isinstance(new.value, float) and math.isnan(new.value)
        tries = len((new.metadata or {}).get("judge_failures", [])) + (0 if unscored else 1)
        outcome = "unscored after retry" if unscored else ("parsed on retry" if tries == 2 else "parsed first time")
        edit_score(
            log, s.id, "rubric_judge",
            ScoreEdit(
                value=new.value, answer=new.answer, explanation=new.explanation,
                reason=new.reason if unscored else None,
                metadata={**(new.metadata or {}), "rescored_from": old.explanation, "rescore_outcome": outcome},
                provenance=ProvenanceData(author="scripts/rescore_judge.py", reason=f"judge rerun: {old.explanation}"),
            ),
            recompute_metrics=False, epoch=s.epoch,
        )
        print(f"  {s.id} epoch {s.epoch}: {outcome}, score {new.value}")
    recompute_metrics(log)
    out = path.with_name(path.stem + "_rescored.eval")
    write_eval_log(log, str(out))
    print(f"Wrote {out}")


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    asyncio.run(rescore(Path(sys.argv[1])))
