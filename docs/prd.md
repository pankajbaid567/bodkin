# PRD: Bodkin

A bodkin is a tailor's needle. Bodkin threads your *proven* claims to each job description.

## Problem
You will own many projects (Pitbook, VITRAM, TaskFlow, Cairn, cache-cluster, soon Counterfoil, Drumlin, Warrantgate). Every JD wants a different 3. Choosing by gut and rewriting bullets by hand is slow, inconsistent, and is exactly where inflated or unverifiable claims creep in. The hiring-research report says the job is *selection and defence*, and that one resume variant per JD type beats a longer resume.

## Product
A local, zero-dependency Python tool.
- **Input:** a job description (pasted text or file) and your **bank**: profile, projects, experience, achievements, each made of *claims* that carry a proof status and a proof command.
- **Output:** the best 3 projects for that JD (and why), the bullets to use for each, a skills section re-ordered for the JD, an eligibility check (CGPA, batch, location), an ATS keyword coverage figure, and an honest **gap analysis** that says which JD skills you have no proven evidence for and which planned portfolio project would close each gap.
- **Honest by construction:** the tool never writes a new sentence. Every bullet it emits is a verbatim text from your bank, every number in a bank text must be declared, claims that are `pending` are never emitted, and a lint refuses phrases you have decided not to claim ("fault-tolerant", "production-grade", ...).

## Users
You, daily (CLI and a local web page), and any reviewer who wants to see how a resume line is backed.

## Goals
1. For a JD, return a ranked and *explained* selection in under 100 ms.
2. Make dishonest output impossible, not just unlikely: provable properties, tested.
3. Make the bank cheap to maintain: one TOML file per project, validated, with proof-path checking against the project repos.
4. Make the portfolio roadmap data-driven: gaps across many JDs show which project to build next.
5. Zero dependencies (Python 3.11+ stdlib only), no network, no telemetry. JDs and the bank never leave the machine.

## Non-goals (v1)
- Writing or rephrasing text with an LLM. (Deliberately: rewriting is where claims drift. A future optional mode could propose variants for *you to add to the bank*, never emit them directly.)
- Fetching JDs from URLs, auto-applying, tracking applications.
- Producing the final PDF (it emits a LaTeX snippet, Markdown, plain text and JSON for your existing resume).
- Predicting whether you will get the job.

## Success metrics (targets set before building; results go in `docs/results.md`)
| Metric | Target |
|---|---|
| Honesty property: output bullets that are not verbatim bank text | 0 across at least 1,000 random JDs |
| Pending claims emitted | 0 across the same runs |
| Determinism | byte-identical output across runs and across `PYTHONHASHSEED` values |
| Selection quality on 14 labelled JDs | at least 80% satisfy their labelled constraints (labels written by the author, disclosed as such, not a benchmark) |
| Speed | a 20 KB JD analysed in under 100 ms; 50 JDs in under 3 s |
| Bug-catching power of the tests | 6 of 6 injected scoring/honesty bugs caught |
| Dependencies | 0 |

## Risks
| Risk | Mitigation |
|---|---|
| Keyword matching misses synonyms and context ("Go" the language vs "go to market") | Taxonomy with aliases, case-sensitive ambiguous aliases, stop-contexts, an "unrecognised terms" list so gaps in the taxonomy are visible; tests with tricky sentences |
| Labelled eval is circular (author labels, author tunes) | Disclosed; labels written before tuning; fixtures are synthetic composites and flagged as such; the honesty properties do not depend on them |
| Stale proof (a claim whose artifact moved) | `claims --check` verifies proof paths exist in the project repo and warns on old dates |
| The bank itself contains an overclaim | Lint + number allow-list + proof status; the final judgement stays with you |
