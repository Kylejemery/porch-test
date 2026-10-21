# The Porch Test: findings

Running log of calibration-stage findings about models' behavior on items in The Porch Test. Each entry is dated, numbered, and backed by log files under `logs/` and transcripts under `review/`.

---

## F1 (October 13, 2026): models collapse "is false" into negation (T1-008 / T1-008b)

**Claim.** On T1-008 and its cued variant T1-008b, both Claude Sonnet 5.5 and GPT-5.5 collapse the Stoic distinction between asserting that a conjunction *is false* and *negating* a conjunction. They classify "'It is both day and night' is false; it is day; therefore it is not night" as the third indemonstrable, which is exactly what Diogenes Laertius VII 78 says it is not. The citation cue in T1-008b moves Claude partially off the error but does not move GPT.

### Uncued (T1-008) vs cued (T1-008b) scores

5 epochs per cell. Model under test / grader shown in each column header.

| epoch | T1-008  Claude · GPT | T1-008  GPT · Claude | T1-008b  Claude · GPT | T1-008b  GPT · Claude |
| --- | --- | --- | --- | --- |
| 1 | 0.25 | 0.25 | **1.00** | 0.25 |
| 2 | 0.25 | 0.25 | 0.25 | 0.375 |
| 3 | 0.25 | 0.375 | **1.00** | 0.25 |
| 4 | 0.25 | 0.25 | 0.25 | 0.25 |
| 5 | 0.25 | 0.25 | 0.25 | 0.25 |
| **mean** | **0.250** | **0.275** | **0.550** | **0.275** |

Cued-vs-uncued delta:

| setup | uncued (T1-008) | cued (T1-008b) | Δ |
| --- | --- | --- | --- |
| Claude under test, GPT grader | 0.250 | 0.550 | **+0.300** |
| GPT under test, Claude grader | 0.275 | 0.275 | **0.000** |

### GPT-5.5 on T1-008b: what it attributes to Diogenes Laertius VII 78

| epoch | score | GPT's claim about DL VII 78 | Claims DL = 3rd indem.? | Correct about DL? |
| --- | --- | --- | --- | --- |
| 1 | 0.25 | Does not quote DL. Concludes the argument is "not merely valid but syllogistic — indeed an indemonstrable" (the third). | Yes (implicit) | No |
| 2 | 0.375 | *"In most reconstructions, however, Diogenes' example is naturally taken as the third indemonstrable."* | Yes (explicit) | No |
| 3 | 0.25 | Does not mention DL. Concludes "it is an instance of the third indemonstrable". | Yes (implicit) | No |
| 4 | 0.25 | *"Diogenes' point is precisely the Stoic inference pattern … specifically the 'not both' indemonstrable."* | Yes (explicit) | No |
| 5 | 0.25 | *"Diogenes Laertius appears to use this very example as a case of a valid but non-syllogistic argument. … Diogenes' treatment at VII 78 is awkward, since he seems to classify it as non-syllogistic despite its obvious reducibility to a canonical Stoic syllogism."* Calls DL (or his source) "careless". | No — reports DL correctly, then argues DL was wrong | Yes about DL; GPT still rules the argument a third indemonstrable itself |

GPT reports DL's actual classification correctly in 1 of 5 epochs, and in that epoch overrides it as mistaken.

### Runs behind the numbers

| key | item | model under test | grader | log |
| --- | --- | --- | --- | --- |
| A | T1-008 | anthropic/claude-sonnet-5-5 | openai/gpt-5.5 | `logs/2026-10-12T20-34-15-00-00_porch-test_Fjz9yrRgAP4vwEiXEXGjob.eval` |
| B | T1-008 | openai/gpt-5.5 | anthropic/claude-sonnet-5-5 | `logs/2026-10-12T20-34-54-00-00_porch-test_L4MmhEvnUFMXsfVFyM2Vqt.eval` |
| C | T1-008b | anthropic/claude-sonnet-5-5 | openai/gpt-5.5 | `logs/2026-10-12T20-35-48-00-00_porch-test_3qgSHikU3iFfoeo66Y62so.eval` |
| D | T1-008b | openai/gpt-5.5 | anthropic/claude-sonnet-5-5 | `logs/2026-10-12T20-36-41-00-00_porch-test_4TFbE9LwhjPXGU4dDnMNgi.eval` |

Full transcripts and per-criterion judge reasons: `review/t1-008.md`.

### Caveats

- n = 5 per cell; stderrs on the means are not negligible and these runs are a calibration probe, not a final result.
- Graders differ between setups, so compare uncued with cued within a row (same grader); comparisons between Claude's row and GPT's row are confounded with the grader.
- The judge has not yet been calibrated against Kyle's blind grades (see RUBRIC_SPEC.md §6.4). Cohen's kappa unknown.

### Supporting runs

Earlier runs with the retired `openai/gpt-5.5-pro` configuration show the same failure, so F1 is not a `gpt-5.5` artifact.

| key | item | model under test | grader | per-epoch | mean | log |
| --- | --- | --- | --- | --- | --- | --- |
| A' | T1-008 | anthropic/claude-sonnet-5-5 | openai/gpt-5.5-pro | 0.25, 0.25, 0.25, 0.25, 0.25 | 0.250 | `logs/2026-10-12T20-06-51-00-00_porch-test_6jK8MQyWemxp7RitNdWu43.eval` |
| B' | T1-008 | openai/gpt-5.5-pro | anthropic/claude-sonnet-5-5 | 0.25, 0.25, 0.25, 0.125, 0.25 | 0.225 | `logs/2026-10-12T20-08-34-00-00_porch-test_QBtkk6xjGJqunGTcbFVV2T.eval` |

T1-008 also scored 0.25 in both earlier cross-track pilots (log `U6gNtygFVEToSLAR87E92b` with Claude under test and `gpt-5.5-pro` grader, and log `goZfAWgGjzQf7UL6T5eZRa` with the same setup after the judge-prompt fixes). Every uncued run failed the same way: four single-item runs (A, B, A′, B′; 20 answers) and both cross-track pilots, each scoring 0.25 ± one criterion.

### Evidence for the gold answer

**Diogenes Laertius, Lives of Eminent Philosophers VII 7.78** (tr. R. D. Hicks, 1925; ledger `S008`, corpus `f9d254ff-01b0-4b37-b98d-9d71132839a9`):

> Of conclusive some are denoted by the common name of the whole class, "conclusive proper," others are called syllogistic. The syllogistic are such as either do not admit of, or are reducible to such as do not admit of, immediate proof in respect of one or more of the premisses; e.g. "If Dion walks, then Dion is in motion; but Dion is walking, therefore Dion is in motion." Conclusive specifically are those which draw conclusions, but not by syllogism; e.g. the statement "It is both day and night" is false: "now it is day; therefore it is not night."

DL puts this very argument on the "conclusive but not syllogistic" side of the line. **Mates** (ledger S008 notes, chunk `78c91994-ccd2-47ac-9eb9-17201baa0783`) reads it the same way: the premise says a conjunction "is false" rather than negating it, and "the Stoics distinguished between the negation of a proposition and the assertion that a proposition is false." Collapsing those two is exactly what the models under test do.

**Lean backing.** The Themata Project represents "'p' is false" as its own operator (`saidFalse` in `Stoic/Syntax.lean`), semantically a negation but syntactically distinct, so no indemonstrable applies to it:

- `Stoic/Tests.lean`: `S008_not_derivable (P : Params) (T : Theory) : ¬ Derives P T [] ⟨[saidFalse (conj p₀ p₁), p₀], neg p₁⟩`.
- `Stoic/Tests.lean` also carries `#guard` checks that this argument is valid under the DL 7.77 criterion.
- `Stoic/Sugihara.lean`: proves S008 underivable under every candidate rule set and every parameter setting, via soundness in the Sugihara model of the relevance logic RM.
