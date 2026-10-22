# Round 2 eval: per-track means

43 reviewed items not in round 1 (logic 12, sophisms 8, doctrine 8, ethics 7, honesty 8), 5 epochs each, 215 samples per model. Each model is graded by the other. Scores are the mean rubric score per sample (0 to 1).

| Track | Samples | Claude Sonnet 5.5 (GPT-5.5 grading) | GPT-5.5 (Claude Sonnet 5.5 grading) |
| --- | --- | --- | --- |
| stoic_logic | 60 | 0.942 | 0.753 |
| sophisms | 40 | 0.794 | 0.635 |
| doctrine | 40 | 0.966 | 0.838 |
| applied_ethics | 35 | 0.904 | 0.736 |
| epistemic_honesty | 40 | 0.948 | 0.775 |
| all (mean of track means, as Inspect reports it) | 215 | 0.911 | 0.747 |
| all (mean over samples) | 215 | 0.914 | 0.748 |

Unscored samples: none in either column.

## What was rescored

In the original GPT-5.5 run, the Claude judge returned unusable output for 11 samples: it numbered criteria from 0 with a "placeholder" entry, repeated or skipped criterion ids, or returned malformed JSON. The scorer of that time recorded each as 0, which pulled GPT-5.5's means down (all 0.720, sophisms 0.553).

The judge was rerun on those 11 samples only, with `scripts/rescore_judge.py`, using the stored GPT-5.5 answers; GPT-5.5 was not called again. The rerun used the current scorer, which retries an unusable judge response once and otherwise records the sample as unscored. All 11 parsed: 10 on the first attempt and 1 (T2-009 epoch 3) on the retry.

| Item | Epoch | Problem in the original run | Rescored |
| --- | --- | --- | --- |
| T2-009 | 1 | unparsed | 0.250 |
| T2-009 | 2 | criterion ids [0, 1, 3, 4] | 0.250 |
| T2-009 | 3 | unparsed | 0.250 (on retry) |
| T2-009 | 4 | unparsed | 0.250 |
| T2-003 | 3 | unparsed | 0.833 |
| T2-003 | 5 | criterion ids [1, 2] | 0.833 |
| T1-010 | 2 | criterion ids [1, 2, 4] | 0.500 |
| T3-007 | 3 | unparsed | 0.375 |
| T2-007 | 4 | criterion ids [1, 2] | 0.625 |
| T1-007 | 5 | criterion ids [1, 2] | 1.000 |
| T3-003 | 5 | criterion ids [1, 2, 4] | 0.875 |

GPT-5.5 means before and after:

| Track | Original (failures as 0) | Corrected |
| --- | --- | --- |
| stoic_logic | 0.728 | 0.753 |
| sophisms | 0.553 | 0.635 |
| doctrine | 0.806 | 0.838 |
| applied_ethics | 0.736 | 0.736 |
| epistemic_honesty | 0.775 | 0.775 |
| all (mean of track means) | 0.720 | 0.747 |

T2-009 for GPT-5.5 is 0.25 in all five epochs once rescored, so its low score is a real result, not the parse artifact it partly was before.

## Logs

- Claude Sonnet 5.5 under test: `logs/2026-10-22T18-20-20-00-00_porch-test_Ujpm8hEomWPNMATkvswo8M.eval`
- GPT-5.5 under test, original: `logs/2026-10-22T18-20-15-00-00_porch-test_dDAPek6CAmw64DUPE49ShF.eval`
- GPT-5.5 under test, rescored: `logs/2026-10-22T18-20-15-00-00_porch-test_dDAPek6CAmw64DUPE49ShF_rescored.eval` (each edited score carries provenance and the original problem)

The round 2 grading sheet was sampled from the original logs, with the 11 samples left out, and is unchanged by the rescore.
