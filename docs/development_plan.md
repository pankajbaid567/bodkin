# Development plan

Checklist; an item is ticked only when its exit criterion is met by a command that can be re-run.

## Phase 0: plan
- [x] Name check, PRD, architecture and algorithm spec, ADRs, test strategy

## Phase 1: taxonomy and JD analysis
- [x] `data/skills.toml` (about 150 skills, aliases, archetype weights, role patterns, cities)
- [x] `taxonomy.py`, `jd.py`: sections, weights, archetypes, eligibility, unrecognised terms
- [x] Tests for tricky matching and eligibility phrasings

## Phase 2: bank
- [x] `bank.py`, `lint.py`; format reference `docs/bank-format.md`
- [x] Seed bank from facts that exist: resume (VITRAM, TaskFlow, in.culcate, achievements), Pitbook claims register, cache-cluster and Cairn docs; each claim marked `proven` or `reported`
- [x] `validate --strict` passes on the seed bank; `claims --check` verifies Pitbook proof paths

## Phase 3: selection and rendering
- [x] `select.py`: greedy selection, bullets, skills order, gaps, coverage
- [x] `render.py`: md, json, tex, txt, batch matrix
- [x] Unit tests with hand-computed scores

## Phase 4: CLI, UI, evaluation
- [x] `cli.py` commands; `server.py` and `web/index.html`
- [x] 12 synthetic JD fixtures with labels; `bodkin eval`
- [x] Honesty property tests (1,000 random JDs), robustness tests
- [x] Mutation check script (5 of 5 caught)

## Phase 5: use it
- [x] Run `batch` over all fixtures, record the matrix and the gap summary in `docs/results.md`
- [x] README
- [ ] Add real JDs to `jds/private/` and rerun `make batch` (decides which portfolio project is next)
- [ ] Re-verify the `reported` claims and flip them to `proven` (VITRAM, TaskFlow, Cairn, cache-cluster)
- [ ] Push to GitHub (name already checked; owner's call)
