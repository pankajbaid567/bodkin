# Bodkin

**Thread your proven claims to each job description.** A bodkin is a tailor's needle.

You will own many projects. Every JD wants a different three. Bodkin takes a JD and your **bank** (projects, experience, achievements, each made of *claims* with a proof status) and returns the best projects for that JD and why, the bullets to use, a re-ordered skills line, an eligibility check, and an honest gap analysis that names the planned project that would close each gap.

> **It selects and orders. It never writes.** Every bullet it prints is verbatim text from your bank, every number in a bank text must be declared, `pending` claims are never used, and a wording lint refuses phrases you decided not to claim ("fault-tolerant", "production-grade", ...). These are tested as properties over 1,000 random JDs and by injecting bugs ([docs/results.md](docs/results.md)).

Zero dependencies (Python 3.11+ standard library). No network, no telemetry: your JDs and your bank never leave the machine.

## Hosting (optional)
`PYTHONPATH=src python -m bodkin serve --public` binds `0.0.0.0`, reads `PORT`, answers only to the host names in `BODKIN_ALLOWED_HOSTS` (Render sets `RENDER_EXTERNAL_HOSTNAME` itself), limits bodies to 100 KB and runs at most 4 analyses at once. Pasted job descriptions are analysed in memory and never stored. The bank it serves is the one in `bank/`, so a public instance shows those resume bullets to anyone.

## Quickstart

```bash
./bodkin validate                                   # check the bank (numbers, wording, proof fields)
./bodkin analyze jd.txt                             # Markdown report for one JD (use - to read stdin)
./bodkin analyze jd.txt --format txt                # resume-ready text
./bodkin analyze jd.txt --format tex --out out/projects.tex   # LaTeX snippet
./bodkin analyze jd.txt --format json               # machine-readable
./bodkin serve                                      # local web page on http://127.0.0.1:8787
./bodkin batch jds/private                          # many JDs: which projects, which gaps, what to build next
./bodkin explain pitbook jd.txt                     # why does this project score what it does
./bodkin eval                                       # labelled JD set (14 synthetic cases)
./bodkin list ; ./bodkin claims --check             # inventory, and proof artifacts exist in the repos
python3 -m unittest discover -s tests -t .          # 70 tests
```
Paste real JDs into `jds/private/` (git-ignored) and run `make batch` to see which planned portfolio project would close the most gaps across *your* target roles.

## What you get for a JD

```
PROJECTS

Cairn – Permission-aware evidence search and decision memory    November 2026
  • Verified generated answers: unsupported claims are dropped; if nothing survives, the reply is a fixed not-found message.
  • Shipped an MCP stdio server with per-agent tokens and ACL-first GitHub sync; revocations answer 503 until applied.
  • Built permission-aware evidence search: answers cite only documents the asker may read, else say "not found".
  • Postgres row-level security plus per-query checks; 50 canary tests find 0 leaks across 5 MCP tools and 2 agents.
...
```
Full example: [examples/atlassian-report.md](examples/atlassian-report.md) (report), [examples/atlassian.tex](examples/atlassian.tex), [examples/genai-resume-text.txt](examples/genai-resume-text.txt).

The report also contains: archetype scores and top skills with the line where the JD said them; eligibility (CGPA, batch, location) against your profile; a ranking of all projects; skills you could truthfully add to your skills line because your projects already use them; JD skills with no proven evidence and the planned project that would close each; and a "read before you use this" list (WIP items, `reported` bullets to re-verify, the limits attached to each bullet).

## How it decides (short version; full spec in [docs/architecture.md](docs/architecture.md))
1. **JD analysis.** A curated taxonomy (about 140 skills, aliases, archetype weights) finds skills; sections weight them (required 1.0, responsibilities 0.8, preferred 0.5, about-us 0.2); repetition adds a capped bonus; inline "is a plus" and "must" adjust a line.
2. **Projects.** Greedy marginal coverage with diminishing returns: three projects that prove the same skill waste two slots. A project must cover at least 3% of the JD's weighted need; otherwise fewer are shown and the rest are marked *supporting, not JD-specific*.
3. **Bullets.** Per project: the most relevant claims, one per group first, using the variant whose archetype the JD points at.
4. **Gaps.** Skills split into listed / claimable (you used it, the skills line does not say so) / no evidence (with the roadmap project that would close it).

## Maintaining the bank
[docs/bank-format.md](docs/bank-format.md). One TOML file per project; every claim has a `proof` (`proven` with a command and a result file, `reported` from a resume or README, `pending`). `./bodkin validate` rejects an undeclared number, banned wording or an unknown skill id; `./bodkin claims --check` verifies that each proof artifact exists in its repo.

## Limits (read these)
- Keyword matching, not understanding: synonyms the taxonomy lacks are missed (the report lists unrecognised terms so you can add them). Context tricks like "Go" the language vs "go to market" are handled; others will exist.
- Eligibility facts come from regular expressions on free text; they are advice, never a filter.
- The labelled evaluation is 14 synthetic JDs labelled by the author, and the numbers after the first run are not independent evidence ([docs/results.md](docs/results.md)).
- LaTeX output is tested structurally but was not compiled on the machine that built it.
- "No evidence in the bank" means the bank lacks it, not that you lack the experience: add the skill and a proven claim.

## Layout
`src/bodkin/` (taxonomy, jd, bank, lint, select, render, evalset, server, cli) · `data/skills.toml`, `data/lint.toml` · `bank/` (profile, roadmap, items) · `jds/fixtures/` (labelled synthetic JDs), `jds/private/` (yours, git-ignored) · `web/index.html` · `tests/` · `scripts/mutation_check.sh` · `docs/`

MIT.
