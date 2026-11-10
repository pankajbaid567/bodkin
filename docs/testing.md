# Testing strategy

Stdlib `unittest` (no pytest), run with `python -m unittest discover -s tests`.

| Layer | Proves |
|---|---|
| Taxonomy tests | aliases compile; `C++`, `C#`, `.NET`, `Node.js`, `CI/CD` match; `Go` matches the language and not `go to market`; case-sensitive aliases; no alias claimed by two skills |
| JD tests | section weights (required beats preferred beats about); repetition raises weight with a cap; archetype scores; many phrasings of CGPA, batch, role type, location; unrecognised terms |
| Bank tests | the shipped bank validates strictly; numbers outside the allow-list are rejected; unknown skill ids are rejected; pending claims are excluded; proof paths are checked |
| Lint tests | every banned phrase is caught; allow-lists work; long bullets are flagged |
| Selection tests | hand-computed scoring examples; greedy avoids redundant picks; diminishing returns; early stop below the minimum gain; WIP penalty; bullet group diversity; variant choice by archetype |
| **Honesty properties** | over at least 1,000 random JDs built from fixture sentences and random text: H1 verbatim bullets, H2 no pending, H4 no banned phrase, H5 determinism (also across `PYTHONHASHSEED`) |
| Robustness | random bytes, empty text, 1 MB input, unicode: no crash and bounded time |
| Rendering | LaTeX escaping of every special character; Markdown and JSON round trip |
| CLI and server | each command's exit status and output shape; the HTTP API with a real local server |
| **Labelled evaluation** | 14 synthetic JDs with constraints (`must`, `one_of`, `must_not`) written before tuning; the pass rate is reported with its limits |
| **Mutation check** | `scripts/mutation_check.sh` injects 6 bugs (ignore section weights, no diminishing returns, emit pending claims, skip the number check, ignore stop phrases, drop the variant threshold) into a scratch copy and requires the suite to fail for each |

Current results and the bugs this suite found in Bodkin itself: `docs/results.md`.

Limits stated up front: fixtures are synthetic composites (the report gives requirements for a few real postings, not their text), and the labelled set is small and author-labelled, so it checks for sanity and regressions, not for general accuracy.

- LaTeX output is checked structurally; it was not compiled because no TeX installation was available.
