# The Porch Test: working notes

## Decisions (October 12, 2026)

1. **Name:** The Porch Test.
2. **Runner:** Inspect (`inspect-ai`), the UK AI Security Institute's open eval framework.
3. **Location:** `C:\Users\kjemery\porch-test`.
4. **Track 1 rests on the Themata ledger.** Items cite ledger ids (`S001` and so on) so the logic track inherits the ledger's verified passages instead of citing from memory.
5. **Themata findings stay out of the public set.** Guardrail 5 of the Themata Project says no public claims before specialist review. So no item's gold answer depends on the project's own results (for example that the first thema is required, or that contraction is needed). T5-005 only states what is uncontroversial.
6. **Contrary versus contradictory.** T1-002 uses "it is not light" instead of Hicks's "it is night", because Hicks's example uses a contrary where the definition requires the contradictory (ledger S002 notes).
7. **Control items.** T5-002 is a genuine quote. Every honesty item that expects "that is fake" needs a matching real quote, so a model cannot score well by doubting everything.

## Review log

October 12, 2026: switched the OpenAI grader and OpenAI-under-test model from `openai/gpt-5.5-pro` to `openai/gpt-5.5`. Earlier calibration runs used `gpt-5.5-pro`; from now on the baseline configuration is `gpt-5.5`.

October 12, 2026: a fresh-eyes review of all 25 drafts found one factual error (T5-003, the quote is Collier's 1701 rendering of Med. 3.9, not a paraphrase of 5.16) and ten rubric, wording and citation fixes. All applied.

## Verification queue

October 12, 2026: 27 sources verified by read-only queries against the Arete Supabase project (`rag_corpus`, `research_sources`). Each verified source carries its chunk or source id in `evidence`. 22 of 25 items now have every source verified.

What verification changed:

1. T1-009 and T1-010 no longer rest only on the Mates summary. Sextus's own text confirms both: M VIII 235 to 236 analyzes the T1-009 form exactly (second then third indemonstrable, intermediate conclusion "potentially contained"), and PH II 147 uses the T1-010 argument as its example of redundancy. These also strengthen ledger entries S013 and S016, which still cite the Mode 2 summary.
2. T1-009 criterion 4 now matches Sextus's wording instead of requiring a named thema.
3. T5-003 gold answer now quotes Long's 3.9 ("Reverence the faculty which produces opinion").
4. T5-005 is confirmed by Bobzien 1996 directly.

Dropped (October 12, 2026): four citations whose texts are not in the corpus (Hierocles via Stobaeus, Gellius VII 2.11, PHerc. 307, Plutarch 1059D to E). The gold answers for T3-003 and T5-004 were reworded so no claim rests on them. Re-add any of them once the text is stored in `research_sources`.

Locators assigned by us: Cicero chunks (On Ends, On Fate, Academica) have no locator in the corpus, so section numbers in those cites come from the content. Worth fixing in the corpus itself.

## Open questions

1. Judge model: which provider grades which? The judge should not grade its own family's answers, or we report that and rerun with a second judge.
2. Second grader: a philosophy graduate student or Stoic scholar for a sample, so calibration is not only Kyle against the judge.
3. Lean refs for T1-009 (S013) and the Sorites item point to harness checks, not named theorems. Name them in `Tests.lean` if we want a clean citation.
4. Private set: start drafting the 30 held back items once the public format settles.

## Next batch (to reach 50 by November 1)

1. Track 1: S009 and S011 (duplicated and indifferently concluding arguments), S010 (compound antecedent), S014 (single premise arguments, Chrysippus against Antipater).
2. Track 2: the Veiled argument, the Liar as a sophism (distinct from T5-004), the Mower if it is attested in the corpus.
3. Track 3: the sage and progress (prokope), cosmopolitanism, the four cardinal virtues as one, cataleptic impressions.
4. Track 4: anger at a family member, ambition and reputation, illness.
5. Track 5: two more fake or paraphrased Marcus quotes and two more genuine controls; one Epictetus quote that is really Enchiridion paraphrase.
