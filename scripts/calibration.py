"""Blind calibration of the judge against Kyle's own scores.

    py -3.14 scripts/calibration.py export
    py -3.14 scripts/calibration.py score

`export` reads the cross-track log and writes one row per rubric criterion to
calibration/round1_grading.xlsx, with the item order shuffled and no model
name or judge information. The judge's scores go to a separate key file,
calibration/round1_judge_key.csv.

`score` joins the filled-in sheet to the key on row_id and writes agreement
statistics (exact agreement, Cohen's kappa, quadratic-weighted kappa) overall
and per track, plus every disagreement, to calibration/round1_report.md.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_GLOB = "*goZfAWgGjzQf7UL6T5eZRa.eval"
OUT_DIR = ROOT / "calibration"
SHEET = OUT_DIR / "round1_grading.xlsx"
KEY = OUT_DIR / "round1_judge_key.csv"
REPORT = OUT_DIR / "round1_report.md"
MIN_TRACK_N = 20
README = OUT_DIR / "README.md"
SEED = 20261012

COLUMNS = [
    "row_id", "item_id", "track", "question", "gold_answer", "model_answer",
    "criterion_number", "criterion_text", "kyle_score", "kyle_note",
]
WIDTHS = {
    "row_id": 8, "item_id": 10, "track": 18, "question": 60, "gold_answer": 60,
    "model_answer": 90, "criterion_number": 10, "criterion_text": 50,
    "kyle_score": 11, "kyle_note": 40,
}

README_TEXT = """# Calibration, round 1

Blind check of the judge against Kyle's own scores.

1. Open `round1_grading.xlsx`. Each row is one rubric criterion for one answer.
2. Score each criterion 0, 1 or 2 in `kyle_score`, using RUBRIC_SPEC.md section 4.
   Add a note in `kyle_note` if useful.
3. Judge the answer's final position. A clearly marked self-correction is not a
   contradiction; leaving the matter unresolved is.
4. Do not open `round1_judge_key.csv` until you have scored every row.

When done, run `py -3.14 scripts/calibration.py score` to write `round1_report.md`.
"""


def find_log() -> Path:
    logs = sorted((ROOT / "logs").glob(LOG_GLOB))
    if not logs:
        sys.exit(f"No log matching logs/{LOG_GLOB}")
    return logs[-1]


def export() -> None:
    from inspect_ai.log import read_eval_log
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    log = read_eval_log(str(find_log()))
    samples = list(log.samples or [])
    random.Random(SEED).shuffle(samples)

    rows: list[list] = []
    key: list[dict] = []
    for s in samples:
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
            key.append({
                "row_id": row_id,
                "judge_score": judged[n]["score"],
                "judge_reason": judged[n].get("reason", ""),
            })

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
    wb.save(SHEET)

    with KEY.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["row_id", "judge_score", "judge_reason"])
        w.writeheader()
        w.writerows(key)

    README.write_text(README_TEXT, encoding="utf-8")
    print(f"Wrote {len(rows)} rows from {len(samples)} samples to {SHEET}")
    print(f"Judge key: {KEY}")


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


def score() -> None:
    from openpyxl import load_workbook

    ws = load_workbook(SHEET, read_only=True).active
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

    with KEY.open(encoding="utf-8") as f:
        judge = {int(r["row_id"]): r for r in csv.DictReader(f)}

    joined = []
    for rid in sorted(kyle):
        j = judge[rid]
        joined.append(kyle[rid] | {"judge_score": int(j["judge_score"]), "judge_reason": j["judge_reason"]})

    by_track: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for r in joined:
        by_track[r["track"]].append((r["kyle_score"], r["judge_score"]))
    overall = [p for ps in by_track.values() for p in ps]

    lines = ["# Calibration, round 1: report", ""]
    lines.append(f"Rows scored: {len(joined)} of {len(joined) + len(blank)}.")
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

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["export", "score"])
    args = parser.parse_args()
    export() if args.command == "export" else score()


if __name__ == "__main__":
    main()
