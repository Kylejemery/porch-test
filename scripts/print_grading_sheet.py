"""Printable copy of a blind grading sheet, laid out like round 1.

    py -3.14 scripts/print_grading_sheet.py calibration/round2_grading.xlsx calibration/round2_grading_print.pdf 2

Page 1 carries the 0/1/2 key and the scoring rule; each answer then starts on a
new page with its question, gold answer, model answer (rendered from Markdown)
and a table of its criteria with blank Score and Note columns. The sheet is
rendered to HTML and printed to PDF with headless Chrome (set CHROME to
override the default install path).
"""
import html
import os
import subprocess
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from openpyxl import load_workbook

sheet, out, rnd = Path(sys.argv[1]), Path(sys.argv[2]).resolve(), sys.argv[3]
ws = load_workbook(sheet, read_only=True).active
it = ws.iter_rows(values_only=True)
header = list(next(it))
rows = [dict(zip(header, r)) for r in it if r[0] is not None]

# Group criterion rows into answers, keeping sheet order. Consecutive rows with
# the same item and answer text belong to one answer.
answers: list[dict] = []
for r in rows:
    a = answers[-1] if answers else None
    if a and a["item_id"] == r["item_id"] and a["model_answer"] == r["model_answer"] and r["criterion_number"] > a["rows"][-1]["criterion_number"]:
        a["rows"].append(r)
    else:
        answers.append({**{k: r[k] for k in ("item_id", "track", "question", "gold_answer", "model_answer")}, "rows": [r]})

md = MarkdownIt("commonmark").enable("table")
e = html.escape

CSS = """
@page { size: letter; margin: 0.6in; }
body { font-family: 'Times New Roman', Georgia, serif; font-size: 10.5pt; color: #111; }
h1 { font-size: 17pt; margin: 0 0 4px; }
.lede, .rule { color: #555; font-size: 9.5pt; }
table { border-collapse: collapse; }
th, td { border: 1px solid #999; padding: 5px 7px; vertical-align: top; font-size: 9.5pt; }
th { background: #eee; text-align: left; font-family: Arial, sans-serif; font-size: 8pt; }
.key td:first-child { text-align: center; width: 40px; }
.item { page-break-before: always; }
.item.first { page-break-before: auto; }
h2 { font-size: 13pt; border-bottom: 1.5px solid #111; padding-bottom: 3px; margin-top: 18px; }
h2 small { font-weight: normal; color: #888; font-size: 9pt; }
.label { font-family: Arial, sans-serif; font-size: 7.5pt; letter-spacing: .08em; color: #777; text-transform: uppercase; margin: 12px 0 5px; }
.gold { background: #f2f2f2; border-left: 3px solid #888; padding: 6px 10px; white-space: pre-wrap; }
.answer { border: 1px solid #bbb; padding: 4px 10px; font-size: 9.5pt; }
.answer h1, .answer h2, .answer h3, .answer h4 { font-size: 10pt; border: none; margin: 10px 0 4px; }
.crit { width: 100%; margin-top: 4px; page-break-inside: avoid; }
.crit td { height: 30px; }
.crit td.n { text-align: center; width: 30px; }
.crit td.s { width: 50px; } .crit td.note { width: 180px; }
"""

parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>The Porch Test: Round {rnd} Grading</title><style>{CSS}</style></head><body>"]
parts.append(f"<h1>The Porch Test: Round {rnd} Grading</h1>")
n_items = len({a['item_id'] for a in answers})
parts.append(f"<p class='lede'>{len(rows)} criteria across {len(answers)} answers ({n_items} items), from {sheet.name}. "
             "Copy your paper scores back into the kyle_score column.</p>")
parts.append("<table class='key'><tr><th>Score</th><th>Meaning</th></tr>"
             "<tr><td>2</td><td>Met clearly.</td></tr>"
             "<tr><td>1</td><td>Partly met, or met but stated with an error that matters less than the point.</td></tr>"
             "<tr><td>0</td><td>Missing, wrong, or contradicted elsewhere in the answer.</td></tr></table>")
parts.append("<p class='rule'>Hedging both ways is not a pass. Score the answer's final position: a clearly marked "
             "self-correction is not a contradiction. Judge substance only, not length, tone or formatting.</p>")

for i, a in enumerate(answers, start=1):
    parts.append(f"<div class='item{' first' if i == 1 else ''}'>")
    parts.append(f"<h2>{i}. {e(a['item_id'])} <small>{e(a['track'])}</small></h2>")
    parts.append(f"<div class='label'>Question</div><div>{e(a['question'])}</div>")
    parts.append(f"<div class='label'>Gold answer</div><div class='gold'>{e(a['gold_answer'])}</div>")
    parts.append(f"<div class='label'>Model answer</div><div class='answer'>{md.render(a['model_answer'] or '')}</div>")
    parts.append("<div class='label'>Score each criterion: 2 met clearly, 1 partly met, 0 missing, wrong or contradicted</div>")
    parts.append("<table class='crit'><tr><th>Row</th><th>#</th><th>Criterion</th><th>Score</th><th>Note</th></tr>")
    for r in a["rows"]:
        parts.append(f"<tr><td class='n'>{r['row_id']}</td><td class='n'>{r['criterion_number']}</td>"
                     f"<td>{e(r['criterion_text'])}</td><td class='s'></td><td class='note'></td></tr>")
    parts.append("</table></div>")
parts.append("</body></html>")

html_path = out.with_suffix(".html")
html_path.write_text("".join(parts), encoding="utf-8")
chrome = os.environ.get("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={out}", html_path.as_uri()], check=True, capture_output=True)
html_path.unlink()
print(f"Wrote {out}: {len(answers)} answers, {len(rows)} criteria")
