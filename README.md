# The Porch Test

A benchmark of whether AI models can reason like a trained Stoic logician and ethicist. Named for the Stoa Poikile, the painted porch in Athens where the school taught.

Status: version 0.1, first draft. Nothing here is public yet.

## Five tracks

| Track | Tests | Items so far |
| --- | --- | --- |
| 1. Stoic logic | The five indemonstrables, the Stoic validity criterion, analysis into indemonstrables, redundancy | 10 |
| 2. Sophisms | The Sorites, the Nobody, the Horned argument | 3 |
| 3. Doctrine | Passions and good feelings, preferred indifferents, oikeiosis, fate and responsibility | 4 |
| 4. Applied ethics | Using the dichotomy of control on real situations | 3 |
| 5. Epistemic honesty | Fake quotes, real quotes, and what the sources cannot tell us | 5 |

Target for version 1.0: about 150 public items and 30 held back privately.

## Layout

```
RUBRIC_SPEC.md          how items are written and scored (read this first)
NOTES.md                decisions and the verification queue
items/track*.json       the items, one file per track
porch_test/task.py      the Inspect task (runner and judge scorer)
scripts/validate_items.py   checks every item against the spec
```

Track 1 items point to the Themata Project ledger (`ledger_ref`) and to the Lean theorems that back their verdicts (`lean_ref`), in `../arete-eval-387/themata/`.

## Setup

```
pip install -r requirements.txt
python scripts/validate_items.py
```

Set API keys for the providers you will use (for example `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).

## Running

Test one model, with a different model as the judge:

```
inspect eval porch_test/task.py --model anthropic/<model> --model-role grader=openai/<model>
```

One track only:

```
inspect eval porch_test/task.py -T track=stoic_logic --model ... --model-role grader=...
```

Only items whose sources are all verified (use this for anything you publish):

```
inspect eval porch_test/task.py -T verified_only=true --model ... --model-role grader=...
```

Open the results viewer:

```
inspect view
```

Scores are reported per track with standard errors. Per criterion judge scores and reasons are in each sample's score metadata, which is what you use for the 20% human calibration.
