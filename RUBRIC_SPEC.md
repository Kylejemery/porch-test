# The Porch Test: Rubric Specification

Version 0.1, drafted October 12, 2026. Status: draft for Kyle's review.

This file defines how every item in The Porch Test is written and scored. If an item and this spec disagree, the spec wins and the item gets fixed.

## 1. What a score means

A model's score on an item is the share of rubric points it earned. A model's score on a track is the mean of its item scores, reported with a 95% confidence interval. We never report a single overall number without the five track scores beside it, because a model can be strong at formal logic and weak at citation honesty, and the average would hide that.

## 2. Item anatomy

Every item has:

| Field | Purpose |
| --- | --- |
| `id` | `T<track>-<number>`, for example `T1-004`. Never reused, even if an item is retired. |
| `track` | One of `stoic_logic`, `sophisms`, `doctrine`, `applied_ethics`, `epistemic_honesty`. |
| `prompt` | Exactly what the model sees. Written the way a curious, informed person would ask. No hints about the expected answer. |
| `gold_answer` | A model answer that would earn full marks. Written in plain prose, two to six sentences. |
| `rubric` | Three to five criteria, each a single checkable claim (see section 3). |
| `exact` | Optional. A machine checkable answer for the parts that have one (for example the indemonstrable number and the verdict). |
| `sources` | Where the gold answer comes from, each with a `status` (see section 5). |
| `ledger_ref` | Optional. The Themata Project ledger id (`S001` and so on) the item rests on. |
| `lean_ref` | Optional. The Lean theorem that backs the verdict. |
| `difficulty` | 1 (a careful reader of an introduction gets it), 2 (needs real study), 3 (specialist). |
| `status` | `draft`, `reviewed`, `held` (kept out of the public set), or `retired`. |

## 3. Writing criteria

Each criterion names one thing a correct answer does or avoids. Good criteria are:

1. **Checkable.** A grader can say yes, partly or no without guessing what you meant. "Names the second indemonstrable" is checkable. "Shows understanding of Stoic logic" is not.
2. **Independent.** Meeting one criterion should not automatically meet another.
3. **About substance, not style.** We do not score length, tone or formatting.
4. **Allowed to be negative.** A criterion can say what the answer must avoid, written as "Does not claim...". This is how we catch pop Stoicism and invented quotes.

Every item must have at least one criterion that a confident but wrong answer would fail. If a plausible wrong answer could score full marks, the rubric is broken.

## 4. The scale

Each criterion is scored:

| Score | Meaning |
| --- | --- |
| 2 | Met clearly. |
| 1 | Partly met, or met but stated with an error that matters less than the point. |
| 0 | Missing, wrong, or contradicted elsewhere in the answer. |

Score the answer's final position. A clearly marked self-correction (where the answer flags an earlier statement as mistaken and settles on a different final position) is not a contradiction. A criterion that the answer leaves unresolved, or that it asserts in one place and contradicts in another without settling, scores 0. Hedging both ways is not a pass.

Item score = points earned / (2 × number of criteria).

## 5. Sources and verification

Every source carries one of three statuses:

| Status | Meaning |
| --- | --- |
| `ledger` | The passage is already in the Themata ledger (`evidence/suite.yaml`), quoted from a retrieved text with a chunk id. Inherits the ledger's confidence. |
| `verified` | Checked against a text in the Arete corpus or `research_sources`. The `evidence` field records the chunk id (`rag_corpus:<id>`) or source id (`research_sources:<id>`, passing `research_source_contains` with attribution and locator). A fact about translation history may be verified from a web source, recorded as `web: <url>`, and says so in `note`. |
| `to_verify` | Drafted from memory. Must be checked before the item can move to `reviewed`. |

This follows the Themata guardrail: no citation from model recall alone. An item with any `to_verify` source cannot enter the public set.

## 6. How scoring runs

1. **Exact checks first.** Where an item has an `exact` block, those fields are checked by code, not by a judge. Track 1 relies on this most.
2. **Judge model for the rest.** The judge sees the prompt, the gold answer, the rubric and the response. It returns, for each criterion, a score and one sentence of reasoning, as JSON. It never sees which model wrote the response.
3. **The judge is not one of the models under test** in the same run, or, if it must be, we report that and rerun with a second judge.
4. **Human calibration.** Kyle blind grades a random 20% of responses, stratified by track, without seeing the judge's scores. We report Cohen's kappa between Kyle and the judge for each track, on the per criterion scores.
5. **Rubric repair rule.** If kappa for a track falls below 0.6, we do not publish that track. We read the disagreements, rewrite the criteria that caused them, and rerun.

## 7. Contamination

About 30 items are held back as a private set. They are never published, never pasted into a chat interface, and only sent through the API. If a model scores far higher on the public set than the private set, we report that as possible contamination.

## 8. What the benchmark does not claim

1. It does not measure whether a model is wise or virtuous. It measures whether a model can reason about Stoic logic and ethics accurately and honestly.
2. A gold answer states the best reading of the sources, and flags it where scholars disagree. Where they disagree, the rubric rewards naming the disagreement, not picking a side.
3. Results built on the Themata Project's own findings (for example which themata are required) stay out of the public set until a specialist in Stoic logic has reviewed that work.
