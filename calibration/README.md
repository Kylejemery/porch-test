# Calibration, round 2

Blind check of the judge against Kyle's own scores.

1. Open `round2_grading.xlsx`. Each row is one rubric criterion for one answer.
2. Score each criterion 0, 1 or 2 in `kyle_score`, using RUBRIC_SPEC.md section 4.
   Add a note in `kyle_note` if useful.
3. Judge the answer's final position. A clearly marked self-correction is not a
   contradiction; leaving the matter unresolved is.
4. Do not open `round2_judge_key.csv` until you have scored every row.

When done, run `py -3.14 scripts/calibration.py score --round 2` to write `round2_report.md`.
