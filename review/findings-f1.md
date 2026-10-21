# The Porch Test: Findings

Pilot findings, recorded as they appear. Each entry states what was run, what was seen, and what it does not yet show.

## F1: models collapse "is false" into negation (T1-008 / T1-008b)

Recorded October 13, 2026. Runs made October 12, 2026.

### Summary

Asked whether "'It is both day and night' is false; it is day; therefore it is not night" is a Stoic syllogism, both Claude and GPT answered that it is a third indemonstrable in every uncued run. Diogenes Laertius (VII 78) gives this exact argument as his example of one that is conclusive but not syllogistic, because asserting that a conjunction is false is not the same as negating it. The Themata Project proves the argument is not derivable from the indemonstrables (`Stoic/Tests.lean: S008_not_derivable`).

When the prompt named the source ("Diogenes Laertius gives this example at VII 78"), Claude answered correctly in 2 of 5 runs. GPT answered correctly in none, and in most runs attributed the wrong classification to Diogenes himself.

### Items

| Item | Prompt | Gold verdict |
| --- | --- | --- |
| T1-008 | The argument alone | Valid, not syllogistic |
| T1-008b | The same, prefixed with "Diogenes Laertius gives this example at VII 78." | Valid, not syllogistic |

### Scores, uncued against cued (standard models)

Under test and grader: `anthropic/claude-sonnet-5-5` and `openai/gpt-5.5`. Each model is graded by the other.

| Setup | T1-008 (uncued) | T1-008b (cued) | Change |
| --- | --- | --- | --- |
| Claude under test, GPT grading | 0.250 | 0.550 | +0.300 |
| GPT under test, Claude grading | 0.275 | 0.275 | 0.000 |

Per run:

| Run | 1 | 2 | 3 | 4 | 5 | Mean |
| --- | --- | --- | --- | --- | --- | --- |
| A. T1-008, Claude under test, GPT grading | 0.25 | 0.25 | 0.25 | 0.25 | 0.25 | 0.250 |
| B. T1-008, GPT under test, Claude grading | 0.25 | 0.25 | 0.375 | 0.25 | 0.25 | 0.275 |
| C. T1-008b, Claude under test, GPT grading | 1.00 | 0.25 | 1.00 | 0.25 | 0.25 | 0.550 |
| D. T1-008b, GPT under test, Claude grading | 0.25 | 0.375 | 0.25 | 0.25 | 0.25 | 0.275 |

Claude's cued scores split into full marks or failure, with nothing between. The citation sometimes retrieves the right reading and sometimes does not.

### What GPT attributes to Diogenes (run D, cued)

| Run | What GPT says about DL VII 78 | Says DL calls it a third indemonstrable? | Correct about DL? |
| --- | --- | --- | --- |
| 1 | Does not engage with DL. Concludes it is "not merely valid but syllogistic, indeed an indemonstrable." | Implicitly | No |
| 2 | "In most reconstructions, however, Diogenes' example is naturally taken as the third indemonstrable." | Explicitly | No |
| 3 | Does not mention DL. Concludes "it is an instance of the third indemonstrable." | Implicitly | No |
| 4 | "Diogenes' point is precisely the Stoic inference pattern ... specifically the 'not both' indemonstrable." | Explicitly | No |
| 5 | Reports DL correctly ("a valid but non-syllogistic argument"), then calls DL's treatment "awkward" and DL or his source "careless," and classifies it as a third indemonstrable anyway. | No | Yes about DL; still wrong in its own verdict |

Three distinct behaviours: misreporting the source (runs 2 and 4), ignoring the cue (runs 1 and 3), and overriding the source by assuming the very equivalence the passage denies (run 5).

### Supporting runs (earlier configuration)

Same item T1-008, uncued, with `openai/gpt-5.5-pro` in place of `gpt-5.5`:

| Setup | Runs | Mean |
| --- | --- | --- |
| Claude under test, GPT-5.5-pro grading | 0.25, 0.25, 0.25, 0.25, 0.25 | 0.250 |
| GPT-5.5-pro under test, Claude grading | 0.25, 0.25, 0.25, 0.125, 0.25 | 0.225 |

T1-008 also scored 0.25 in both cross-track pilots. Every uncued run across both configurations failed in the same way.

### Logs

| Run | Log |
| --- | --- |
| A | `logs/2026-10-12T20-34-15-00-00_porch-test_Fjz9yrRgAP4vwEiXEXGjob.eval` |
| B | `logs/2026-10-12T20-34-54-00-00_porch-test_L4MmhEvnUFMXsfVFyM2Vqt.eval` |
| C | `logs/2026-10-12T20-35-48-00-00_porch-test_3qgSHikU3iFfoeo66Y62so.eval` |
| D | `logs/2026-10-12T20-36-41-00-00_porch-test_4TFbE9LwhjPXGU4dDnMNgi.eval` |
| Supporting, Claude under test | `logs/2026-10-12T20-06-51-00-00_porch-test_6jK8MQyWemxp7RitNdWu43.eval` |
| Supporting, GPT-5.5-pro under test | `logs/2026-10-12T20-08-34-00-00_porch-test_QBtkk6xjGJqunGTcbFVV2T.eval` |

Full transcripts and judge reasons: `review/t1-008.md`.

### Evidence for the gold answer

1. Diogenes Laertius VII 78 (tr. Hicks 1925): "Conclusive specifically are those which draw conclusions, but not by syllogism; e.g. the statement 'It is both day and night' is false: 'now it is day; therefore it is not night.'" Themata ledger S008, confidence high.
2. Mates's reading (Mode 2 summary in the corpus): the Stoics distinguished negating a proposition from asserting that it is false.
3. Lean: `S008_not_derivable` (not derivable from the base cases) and `Stoic/Sugihara.lean` (underivable under every candidate and setting).

### Caveats

n = 5 per cell. Graders differ by setup, so compare uncued with cued within a row, not Claude with GPT across rows. The judge is not yet calibrated against human grading (round 1 in progress). One model per provider. Treat as a strong pilot signal, not a measured rate.
