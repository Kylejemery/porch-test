"""Blind calibration of the judge against Kyle's own scores.

    py -3.14 scripts/calibration.py export
    py -3.14 scripts/calibration.py score
    py -3.14 scripts/calibration.py export --round 2 --log logs/A.eval --log logs/B.eval
    py -3.14 scripts/calibration.py score --round 2

`export` reads the cross-track log and writes one row per rubric criterion to
calibration/roundN_grading.xlsx, with the item order shuffled and no model
name or judge information. The judge's scores go to a separate key file,
calibration/roundN_judge_key.csv.

Round 1 exports every criterion of one log. From round 2 on, `export` takes
one or more logs (one per model under test) and samples whole answers per
track, alternating between logs, until each track has at least MIN_TRACK_N
criteria. The key also records which model and epoch each row came from.

`score` joins the filled-in sheet to the key on row_id and writes agreement
statistics (exact agreement, Cohen's kappa, quadratic-weighted kappa) overall
and per track, plus every disagreement, to calibration/roundN_report.md.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_GLOB = "*goZfAWgGjzQf7UL6T5eZRa.eval"
OUT_DIR = ROOT / "calibration"
MIN_TRACK_N = 20
README = OUT_DIR / "README.md"
SEED = 20261012
SEEDS = {1: SEED, 2: 20261022}


def paths(rnd: int) -> tuple[Path, Path, Path]:
    """Sheet, judge key and report for a calibration round."""
    return (OUT_DIR / f"round{rnd}_grading.xlsx",
            OUT_DIR / f"round{rnd}_judge_key.csv",
            OUT_DIR / f"round{rnd}_report.md")

COLUMNS = [
    "row_id", "item_id", "track", "question", "gold_answer", "model_answer",
    "criterion_number", "criterion_text", "kyle_score", "kyle_note",
]
WIDTHS = {
    "row_id": 8, "item_id": 10, "track": 18, "question": 60, "gold_answer": 60,
    "model_answer": 90, "criterion_number": 10, "criterion_text": 50,
    "kyle_score": 11, "kyle_note": 40,
}

README_TEXT = """# Calibration, round {n}

Blind check of the judge against Kyle's own scores.

1. Open `round{n}_grading.xlsx`. Each row is one rubric criterion for one answer.
2. Score each criterion 0, 1 or 2 in `kyle_score`, using RUBRIC_SPEC.md section 4.
   Add a note in `kyle_note` if useful.
3. Judge the answer's final position. A clearly marked self-correction is not a
   contradiction; leaving the matter unresolved is.
4. Do not open `round{n}_judge_key.csv` until you have scored every row.

When done, run `py -3.14 scripts/calibration.py score{flag}` to write `round{n}_report.md`.
"""


def find_log() -> Path:
    logs = sorted((ROOT / "logs").glob(LOG_GLOB))
    if not logs:
        sys.exit(f"No log matching logs/{LOG_GLOB}")
    return logs[-1]


def sample_answers(logs: list, rnd: int) -> list[tuple]:
    """Pick whole answers per track, alternating between logs, until each
    track has at least MIN_TRACK_N criteria. Items not yet picked are
    preferred, so the sample spreads across items before repeating one.
    Answers whose judge output did not parse are left out and reported."""
    rng = random.Random(SEEDS.get(rnd, rnd))
    queues: dict[str, list[list]] = defaultdict(lambda: [[] for _ in logs])
    skipped = []
    for li, log in enumerate(logs):
        for s in log.samples or []:
            if is_unscored(s):
                skipped.append(f"{log.eval.model} {s.id} epoch {s.epoch}")
                continue
            queues[s.metadata["track"]][li].append((log, s))
    for qs in queues.values():
        for q in qs:
            rng.shuffle(q)

    picked: list[tuple] = []
    for track in sorted(queues):
        qs, used, n, turn = queues[track], set(), 0, 0
        while n < MIN_TRACK_N and any(qs):
            q = qs[turn % len(qs)]
            turn += 1
            if not q:
                continue
            i = next((k for k, (_, s) in enumerate(q) if s.id not in used), 0)
            log, s = q.pop(i)
            used.add(s.id)
            n += len(s.metadata["rubric"])
            picked.append((log, s))
        if n < MIN_TRACK_N:
            print(f"Warning: {track} has only {n} criteria available")
    rng.shuffle(picked)
    for line in skipped:
        print(f"Left out, judge output unparsed: {line}")
    return picked


def export(rnd: int, log_paths: list[str]) -> None:
    from inspect_ai.log import read_eval_log
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    sheet, key_path, _ = paths(rnd)
    if rnd == 1:
        log = read_eval_log(str(find_log()))
        samples = list(log.samples or [])
        random.Random(SEED).shuffle(samples)
        answers = [(log, s) for s in samples]
    else:
        if not log_paths:
            sys.exit("Round 2 and later need --log for each model under test.")
        answers = sample_answers([read_eval_log(p) for p in log_paths], rnd)

    rows: list[list] = []
    key: list[dict] = []
    for log, s in answers:
        score = s.scores["rubric_judge"]
        md = score.metadata or {}
        if md.get("parse_failed"):
            sys.exit(f"Sample {s.id} has an unparsed judge score; rescore before calibrating.")
        judged = {int(c["n"]): c for c in md["criteria"]}
        for n, text in enumerate(s.metadata["rubric"], start=1):
            row_id = len(rows) + 1
            rows.append([
                row_id, s.id, s.metadata["track"], s.input, s.target,
                s.output.completion, n, text, None, None,
            ])
            entry = {
                "row_id": row_id,
                "judge_score": judged[n]["score"],
                "judge_reason": judged[n].get("reason", ""),
            }
            if rnd > 1:
                entry |= {"model": log.eval.model, "epoch": s.epoch}
            key.append(entry)

    OUT_DIR.mkdir(exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "grading"
    ws.append(COLUMNS)
    for r in rows:
        ws.append(r)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = wrap
    for i, name in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = WIDTHS[name]
    ws.freeze_panes = "A2"

    score_col = get_column_letter(COLUMNS.index("kyle_score") + 1)
    dv = DataValidation(
        type="list", formula1='"0,1,2"', allow_blank=True,
        showErrorMessage=True, errorTitle="Invalid score", error="Enter 0, 1 or 2.",
    )
    ws.add_data_validation(dv)
    dv.add(f"{score_col}2:{score_col}{len(rows) + 1}")
    wb.save(sheet)

    with key_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key[0]))
        w.writeheader()
        w.writerows(key)

    flag = "" if rnd == 1 else f" --round {rnd}" + "".join(f" --log {Path(p).as_posix()}" for p in log_paths)
    README.write_text(README_TEXT.format(n=rnd, flag=flag), encoding="utf-8")
    print(f"Wrote {len(rows)} rows from {len(answers)} samples to {sheet}")
    print(f"Judge key: {key_path}")


def _ac1(pairs: list[tuple[int, int]], q: int = 3) -> float:
    """Gwet's AC1 for two raters. Unlike kappa it stays stable when nearly
    every score falls in one category (the prevalence problem)."""
    n = len(pairs)
    pa = sum(a == b for a, b in pairs) / n
    pi = [(sum(a == c for a, _ in pairs) + sum(b == c for _, b in pairs)) / (2 * n) for c in range(q)]
    pe = sum(p * (1 - p) for p in pi) / (q - 1)
    return (pa - pe) / (1 - pe)


def _stats(pairs: list[tuple[int, int]]) -> tuple[str, str, str, str]:
    from sklearn.metrics import cohen_kappa_score

    if not pairs:
        return "n/a", "n/a", "n/a", "n/a"
    k, j = zip(*pairs)
    agree = sum(a == b for a, b in pairs) / len(pairs)

    def kappa(weights: str | None) -> str:
        # Undefined when both raters use a single identical category.
        if len(set(k) | set(j)) < 2:
            return "undefined"
        return f"{cohen_kappa_score(k, j, labels=[0, 1, 2], weights=weights):.3f}"

    return f"{agree:.1%}", kappa(None), kappa("quadratic"), f"{_ac1(pairs):.3f}"


def is_unscored(s) -> bool:
    """A sample the judge did not score: marked unscored (NaN) by the current
    scorer, or parse_failed (scored 0) by the scorer before it retried."""
    sc = s.scores["rubric_judge"]
    return bool((sc.metadata or {}).get("parse_failed")) or (
        isinstance(sc.value, float) and math.isnan(sc.value))


def unscored_line(rnd: int, log_paths: list[str]) -> str:
    from inspect_ai.log import read_eval_log

    if rnd == 1 and not log_paths:
        log_paths = [str(find_log())]
    if not log_paths:
        return "Unscored samples in the source logs: not counted (pass --log for each source log)."
    samples = [s for p in log_paths for s in read_eval_log(p).samples or []]
    n = sum(is_unscored(s) for s in samples)
    return f"Unscored samples in the source logs, left out of the sheet: {n} of {len(samples)}."


def score(rnd: int, log_paths: list[str]) -> None:
    from openpyxl import load_workbook

    sheet, key_path, report = paths(rnd)
    ws = load_workbook(sheet, read_only=True).active
    it = ws.iter_rows(values_only=True)
    header = list(next(it))
    kyle = {}
    blank = []
    for values in it:
        r = dict(zip(header, values))
        if r["row_id"] is None:
            continue
        rid = int(r["row_id"])
        if r["kyle_score"] in (None, ""):
            blank.append(rid)
            continue
        s = int(r["kyle_score"])
        if s not in (0, 1, 2):
            sys.exit(f"row {rid}: kyle_score {s} is not 0, 1 or 2")
        kyle[rid] = r | {"kyle_score": s}

    with key_path.open(encoding="utf-8") as f:
        judge = {int(r["row_id"]): r for r in csv.DictReader(f)}

    joined = []
    for rid in sorted(kyle):
        j = judge[rid]
        joined.append(kyle[rid] | {"judge_score": int(j["judge_score"]), "judge_reason": j["judge_reason"]})

    by_track: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for r in joined:
        by_track[r["track"]].append((r["kyle_score"], r["judge_score"]))
    overall = [p for ps in by_track.values() for p in ps]

    lines = [f"# Calibration, round {rnd}: report", ""]
    lines.append(f"Rows scored: {len(joined)} of {len(joined) + len(blank)}.")
    lines.append(unscored_line(rnd, log_paths))
    if blank:
        lines.append(f"Unscored rows, left out: {', '.join(map(str, blank))}.")
    lines += ["", "## Agreement", "",
              "| Scope | n | Exact agreement | Cohen's kappa | Quadratic-weighted kappa | Gwet's AC1 |",
              "| --- | --- | --- | --- | --- | --- |"]
    lines.append(f"| Overall | {len(overall)} | " + " | ".join(_stats(overall)) + " |")
    for track in sorted(by_track):
        lines.append(f"| {track} | {len(by_track[track])} | " + " | ".join(_stats(by_track[track])) + " |")

    lines += ["", f"Publication rule (RUBRIC_SPEC 6.5): a track is judged on its own only with at least {MIN_TRACK_N} "
              "scored criteria; it then needs exact agreement of 80% or more and AC1 of 0.6 or more."]
    small = [t for t in sorted(by_track) if len(by_track[t]) < MIN_TRACK_N]
    if small:
        lines.append(f"Below the minimum this round: {', '.join(small)}. Read their disagreements instead.")

    disagreements = [r for r in joined if r["kyle_score"] != r["judge_score"]]
    lines += ["", f"## Disagreements ({len(disagreements)})", ""]
    if disagreements:
        lines += ["| row | Item | Criterion | Kyle | Judge | Judge's reason | Kyle's note |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in disagreements:
            cells = [
                str(r["row_id"]), r["item_id"],
                f'{r["criterion_number"]}. {r["criterion_text"]}',
                str(r["kyle_score"]), str(r["judge_score"]),
                r["judge_reason"], r.get("kyle_note") or "",
            ]
            lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    else:
        lines.append("None.")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {report}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["export", "score"])
    parser.add_argument("--round", type=int, default=1, dest="rnd")
    parser.add_argument("--log", action="append", default=[], help="eval log (round 2 on); repeat per model")
    args = parser.parse_args()
    export(args.rnd, args.log) if args.command == "export" else score(args.rnd, args.log)


if __name__ == "__main__":
    main()
