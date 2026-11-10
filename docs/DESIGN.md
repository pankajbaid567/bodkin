# DESIGN.md: decisions (short ADRs)

## ADR-000: Name
**Accepted.** *Bodkin* (a tailor's needle). GitHub search 2026-11-10: 26 repos named like it, none about resumes (a Go decoding library, a Robinhood-chain tool). Rejected: `loadout` (1,787 repos including a coding-assistant manager with 100+ stars), `fitcheck`, `jdfit` and `proofcv` (same niche, tiny), `claimcheck`, `selvage`.

## ADR-001: Select and re-order, never write
**Accepted.** The tool only chooses among texts you wrote. Rewriting with an LLM is where claims drift, and drifting claims are the failure the whole portfolio standard exists to prevent. Variants per archetype are written by you, once, in the bank.

## ADR-002: Deterministic, pure, local
**Accepted.** Output is a pure function of inputs (no clock, no randomness, no network); ties are broken by id. This makes the golden tests and the honesty properties checkable, and keeps JDs and the bank private.

## ADR-003: Honesty is enforced by data rules and tests
**Accepted.** Proof status per claim (`proven`, `reported`, `pending`); numbers must be declared (allow-list) so a bullet cannot drift from its evidence; a wording lint mirrors the "what not to claim" rules from the Pitbook claims register; properties H1 to H5 are tested over random JDs. `reported` means "from your resume or a README, not re-run by the tool's author"; it is shown with a marker in reports so you know what to re-verify.

## ADR-004: TOML, standard library only
**Accepted.** `tomllib` is in Python 3.11+; no YAML dependency, no build step, `python -m bodkin` works from a clone. Cost: no TOML writing (the tool never writes the bank).

## ADR-005: Keyword taxonomy, not embeddings
**Accepted.** A curated skill taxonomy with aliases and archetype weights is explainable ("matched `go` in a *required* line, weight 1.0"), instant, and testable. Embeddings would need a model download, would not be explainable, and would blur the honesty story. The taxonomy's blind spots are surfaced (unrecognised terms) instead of hidden.

## ADR-006: Greedy marginal coverage for the top 3
**Accepted.** "Best 3" is a set problem, not a sort: three projects that all prove the same skill waste two slots. Greedy selection with diminishing returns (0.85 per covered unit) is simple, deterministic, explainable, and close to optimal for this coverage-style objective. Rejected: sorting by score (redundant picks), exhaustive search (not needed for K=3 but harder to explain).

## ADR-007: WIP items are allowed, flagged, and penalised
**Accepted.** A project that is built but not yet public (for example Cairn, cache-cluster) can still be the right pick; it gets a 0.7 factor and a warning ("no public repo or demo yet"). Archived items are excluded unless asked.

## ADR-008: Gap analysis feeds the roadmap
**Accepted.** Gaps are split into "listed", "claimable (you already used it; add it to the skills line)" and "no evidence". For the last group the tool names the roadmap projects whose skills would close it. Run over many JDs, this answers which portfolio project to build next from data instead of guesses.

## ADR-009: Local web UI is a thin client
**Accepted.** `bodkin serve` binds `127.0.0.1` only, serves one HTML page, and exposes `POST /api/analyze` that returns the same JSON as the CLI. No logic lives in the browser, so there is one implementation to test.

## ADR-010: Eligibility is advice, not a filter
**Accepted.** CGPA, batch and location facts are extracted with confidence and the matched text, compared with the profile, and shown as warnings. Regex extraction from free text is fallible; the tool never hides a project because of it.

## ADR-011: A project must earn its slot (relative stop rule), and fillers are marked
**Accepted.** The first stop rule was an absolute gain threshold (0.05). Gains scale with the JD's total weighted need (the quant JD's first pick scored 5.1, the data-platform JD's 1.35), so the same threshold padded weak picks in one JD and was meaningless in another. The rule is now relative: a project is recommended only if it covers at least 3% of the JD's total weighted need. When fewer than the requested number qualify, the remaining slots are filled with the strongest proven projects, **explicitly marked "supporting, not JD-specific"** (disable with `--no-fill`), and the evaluation judges only the relevant picks. This matches the report's advice (3 projects, 2 if the third is weak) and keeps fillers from flattering the numbers.

## ADR-012: Worst-case input must be cheap
**Accepted.** JD text is untrusted input (pasted from anywhere). Matching and weighting are O(n log n) in the number of hits, per-line work is done once per line, and a robustness test feeds 1 MB inputs and a single 700 KB line. Two quadratic bugs were found and fixed this way (docs/results.md).

## ADR-013: Show the strongest evidence, not the first
**Accepted.** For each skill the report shows the mention with the highest section weight, so "Python" is explained by the requirements line, not by a marketing sentence in "About us".
