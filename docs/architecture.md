# Architecture

```
 JD text ──► jd.py ──► JDProfile {skill weights, archetype scores, eligibility facts, unknown terms}
                          │
 bank/*.toml ──► bank.py ─┤──► select.py ──► Selection {projects, bullets, experience, achievements, skills order, gaps, coverage}
 data/skills.toml ─► taxonomy.py ┘                │
                                                  ▼
                                   render.py ──► md | json | tex | txt        server.py ──► local web UI
```
Everything is a pure function of (JD text, bank, taxonomy, options). No clock, no randomness, no network (ADR-002).

## Modules
| Module | Responsibility |
|---|---|
| `taxonomy.py` | Loads `data/skills.toml` (skills, aliases, archetype weights, role patterns, city list); compiles matchers; validates |
| `jd.py` | Normalises text, detects sections, extracts skill weights, archetype scores, eligibility facts (CGPA, batch, role type, location), unrecognised terms |
| `bank.py` | Loads and validates profile, items, claims, roadmap; number allow-list; proof status; proof-path check |
| `lint.py` | Wording rules from `data/lint.toml` (banned phrases, length, weak openers) |
| `select.py` | Item scoring, greedy marginal-coverage selection, bullet selection and variant choice, skills re-ordering, gap analysis, coverage |
| `render.py` | Markdown report, JSON, LaTeX snippet (escaped), plain text; the batch matrix |
| `evalset.py` | Labelled-JD evaluation (`must`, `one_of`, `must_not`) |
| `server.py` | `127.0.0.1` HTTP server: serves `web/index.html`, `POST /api/analyze` |
| `cli.py` | Commands: `validate`, `analyze`, `batch`, `list`, `claims`, `explain`, `eval`, `gaps`, `serve` |

## Data model (details in `docs/bank-format.md`)
- **Item** (`bank/items/<id>.toml`): `kind` = project | experience | achievement; `status` = shipped | wip | archived; display fields; `skills` and `archetypes` as `id = strength` (0..1); `tech` list for display; optional `repo` path for proof checks; a list of **claims**.
- **Claim**: `text` (default bullet), optional `variants.<archetype>` texts, `numbers` (allow-list of every number appearing in any text), optional `skills`/`archetypes` overrides, optional `group` (to avoid two bullets of one kind), and `proof` = {`status` = proven | reported | pending, `command`, `artifact`, `date`, `limits`}.
- **Profile**: person facts used for eligibility (batch, CGPA, locations) and the resume's skills categories.
- **Roadmap** (`bank/roadmap.toml`): planned projects with skills and archetypes, used only to answer "which planned project would close this gap".

## Algorithms (the spec the code follows)

### 1. JD analysis
1. Normalise: NFKC, replace odd bullets/dashes, collapse whitespace, keep line structure.
2. Section detection per line: a short line (at most 60 characters) matching a header pattern sets the current section. Weights: `required` 1.0, `responsibilities` 0.8, `body` 0.7, `preferred` 0.5, `about` 0.2 (company marketing, benefits).
3. Skill matching: for every skill, every alias, a compiled regex with token boundaries that also works for `C++`, `C#`, `.NET`, `Node.js`, `CI/CD`. Aliases flagged case-sensitive (for example `Go`, `R`, `C`) only match with exact case and are rejected inside stop-contexts (`go to market`, `go-getter`, `to go`). Each occurrence has its line's section weight.
4. Skill weight: `raw[s] = min(1.5, max_section_weight + 0.25 * log2(count))`, then `weight[s] = raw[s] / max(raw)` so weights are in (0, 1].
5. Archetype scores: `A[a] = sum_s weight[s] * skill[s].archetypes[a]`, plus a fixed bonus of 1.0 when a role pattern for `a` appears in the first 6 lines (the title). Normalised so the maximum is 1.
6. Eligibility facts by regex, each with the matched text and a confidence: minimum CGPA (or percentage), graduation year or batch, role type (intern, new grad, SDE-1, experience range), cities and remote/hybrid. Compared with the profile: `ok`, `fail` or `unknown`.
7. Unrecognised terms: capitalised tokens that appear at least twice and are not in the taxonomy or a stoplist, so you can see what the taxonomy missed.

### 2. Selection (projects)
Needs: `need["s:"+skill] = weight[s]` and `need["a:"+arch] = 0.6 * A_norm[a]`.
Item coverage `cov_i[key]` from the item's `skills` and `archetypes` strengths.
Quality `q_i = status_factor * proof_factor * recency`: status shipped 1.0, wip 0.7, archived 0.4 (excluded unless asked); `proof_factor = 0.7 + 0.3 * (proven claims / eligible claims)`; recency 1.0 within 12 months, falling linearly to 0.85 at 36 months. An item with no eligible claim is skipped (nothing honest to write).
Greedy loop, up to K (default 3): `gain_i = q_i * sum_key need_rem[key] * cov_i[key]`; pick the largest (ties broken by id); stop early if the best gain is below 0.05 (report "no further relevant project"); then `need_rem[key] *= 1 - 0.85 * cov_i[key]` (diminishing returns, so the second project still reinforces important skills but mostly covers new ones). Every item also gets a stand-alone score for the full ranking table, and the top contributing keys are recorded as the explanation.

### 3. Bullets
Per chosen item, eligible claims (proven or reported; pending only with the flag). Claim relevance `r_c = sum_key need[key] * cov_c[key] + 0.15 * has_numbers + 0.10 * proven`, where claim coverage uses the claim's own skills (or the item's, scaled by 0.7). Choose the top B (default 4) with at most one per `group` until groups run out; present in descending relevance. The text is the variant whose archetype has the highest `A_norm` for this JD, falling back to the default text. **Nothing is generated.**

### 4. Experience, achievements, skills, gaps
Experience: all items shown, bullets re-ordered by relevance. Achievements: top N by relevance. Skills: within each profile category, skills the JD mentions come first (by weight), the rest keep their order; nothing is added. Gaps, per JD skill with weight at least 0.3: (a) already listed in the profile, (b) *claimable*: the bank shows real use but the profile does not list it (suggest adding, with the evidence), (c) *no evidence*: with the roadmap projects that would close it. Coverage = weight covered by (profile skills + chosen items) / total weight.

## Honesty properties (tested as properties, ADR-003)
H1 every emitted bullet is byte-identical to some bank text; H2 no `pending` claim is emitted without the explicit flag; H3 every number in every bank text is in its claim's `numbers`; H4 no lint-banned phrase is emitted; H5 output is a pure function of its inputs.
