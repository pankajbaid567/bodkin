# Results

Everything here was produced by commands in this repo (2026-11-10, Python 3.14, macOS). Limits are stated next to each number.

## Test suite
`python3 -m unittest discover -s tests -t .`: **70 tests, all pass, 6 s.** Covers the taxonomy, JD analysis (including 14 phrasings of CGPA and batch), bank validation, hand-computed selection arithmetic, rendering, the CLI, the local server, and the honesty properties.

## Honesty properties (docs/architecture.md, H1 to H5)
Over **1,000 random JDs** (fixture sentences mixed with random taxonomy words, headings and garbage, random options) against a bank that also contains a project whose only claims are *pending*:
- H1: every emitted bullet is verbatim bank text: 0 violations
- H2: no pending claim emitted without `--include-pending` (and it *is* usable with the flag): 0 violations
- H3: every number in every emitted bullet is declared in its claim: 0 violations
- H4: no banned phrase emitted: 0 violations
- H5: identical output in-process and across `PYTHONHASHSEED` 0, 1 and 12345

## Do the tests catch bugs?
`scripts/mutation_check.sh` injects 6 deliberate bugs into a scratch copy (section weights ignored, no diminishing returns, pending claims emitted, undeclared numbers accepted, stop phrases ignored, variants chosen without a relevance threshold): **6 of 6 caught.**

## Bugs the tests found in Bodkin itself
| Found by | Bug | Fix |
|---|---|---|
| first real run | `python` and `java` never matched (their aliases listed only versions, not the name) | a skill's display name is an alias unless it must match case-sensitively |
| eval | the stop rule was an absolute gain threshold, but gains scale with each JD's total weight, so it padded weak third projects | the next project must cover at least 3% of the JD's weighted need (ADR-011) |
| robustness test | overlap removal compared every hit with every other hit (quadratic): a 1 MB JD would take hours | sort-and-sweep, O(n log n): 1 MB now 0.4 s |
| robustness test | each hit re-scanned its whole line to compute the line weight (quadratic on one huge line) | weight computed once per line |
| render test | `UnboundLocalError` in the LaTeX renderer (`L +=` inside a nested function) | `extend` |
| select test | a dataclass field inserted mid-class while the constructor was positional put a list into `share` | keyword construction |
| review of output | a language name alone implied a domain (C++ gave low-latency 0.9, so a generic JD got a low-latency bullet variant) | language archetype weights lowered |

## Speed
A 20 KB JD analyses in about **30 ms** (target 100 ms); a 1 MB JD in 0.4 s; 100,000 repetitions of one word on a single line in 0.3 s.

## Selection quality on the labelled set (`./bodkin eval`)
14 synthetic JDs with constraints (`must`, `one_of`, `must_not`, `gap`) in `jds/fixtures/`. **Current: 14 of 14.**
How to read it honestly:
- The labels were written before the first run. The first run scored **12 of 14**; the two misses exposed the scale-dependent stop rule above, which was fixed for a reason independent of the labels. Numbers after that fix are therefore **not** independent evidence.
- The JD texts are synthetic composites of typical wording (four are paraphrased from requirements recorded in the hiring report). They check sanity and catch regressions; they do not measure accuracy on real postings.
- Fillers (supporting projects shown when fewer than 3 are relevant) are not judged.

## What the batch run says about the portfolio (`./bodkin batch jds/fixtures`)
See `docs/batch-fixtures.md`. **The mix of JDs is mine, so treat it as a demonstration of the method, not as market data.** Add real JDs to `jds/private/` and rerun `make batch` for your own answer. On this mix:
- Pitbook is chosen for 11 of 14 JDs, VITRAM 9, TaskFlow 7, cache-cluster 4, Cairn 3.
- Largest skill with no proven evidence in the bank: **Java** (weight 4.42; it is asked for in several of the report's real posting notes too). Then Payments, Operating systems, Transactions, Scala.
- Planned project that would close the most weight: **Counterfoil** (4.91), then user-space TCP/OS (3.84), MiniDB (3.03), Concurrency lab (2.48). Drumlin scores low here only because few fixtures ask for storage or consensus; that depends entirely on which JDs you feed in.
- "No evidence in the bank" is not "no experience": if you did use a skill, add it to the item's `skills` (and a proven claim) and the gap disappears.
- Skills you could truthfully add to the resume's skills line because your projects already use them: DSA, Concurrency, System design, REST APIs, Database design, Go.

## Not verified
- LaTeX output is checked structurally (escaping, balanced environments) but was **not compiled** (no TeX installation on the machine).
- Eligibility extraction uses regular expressions on free text: tested on 14 phrasings, not on real postings.
- `reported` claims (VITRAM, TaskFlow, Cairn, cache-cluster, experience, achievements) come from your resume and READMEs and were not re-run.
