# Bank format

The bank is a folder of TOML files you edit by hand. Bodkin never writes to it. After any edit run `./bodkin validate` (add `--strict` to treat warnings as errors) and `./bodkin claims --check` (proof artifacts exist in the project repos).

```
bank/
  profile.toml        who you are + your resume's skills section
  roadmap.toml        planned projects (used only for gap analysis)
  items/<id>.toml     one file per project, experience entry or achievement
```

## profile.toml
```toml
[person]
name = "Pankaj Baid"
batch = 2028            # graduation year, for the eligibility check
cgpa = 8.618
locations_ok = ["bengaluru", "hyderabad", "remote"]   # empty = no preference

[skills]                # your resume's skills section; Bodkin re-orders it, never adds to it
"Computer Language" = ["Python", "JavaScript", "C++", "TypeScript", "SQL"]
```

## items/<id>.toml
```toml
id = "pitbook"                      # lowercase letters, digits, dashes
kind = "project"                    # project | experience | achievement
name = "Pitbook"
title = "Pitbook – Crash-safe matching engine and live order book"   # heading text on the resume
subtitle = ""                       # e.g. the employer, for experience
status = "shipped"                  # shipped | wip | archived
date = "November 2026"              # shown on the resume
end = "2026-11"                     # YYYY-MM, drives the recency factor (empty = no decay)
repo = "../../Pitbook"              # path relative to the bank folder, for `claims --check`
tech = ["Go", "React"]              # display only
links = { github = "https://...", demo = "https://..." }
archetypes = { systems = 1.0, backend = 0.8 }        # what kind of work this shows (0..1)
skills = { go = 1.0, wal = 1.0, concurrency = 0.9 }  # skill ids from data/skills.toml (0..1)
note = "Shown as a warning when this item is used."
```
`status = "wip"` items are allowed but penalised (x0.7) and flagged ("no public repo or demo yet"). `archived` items are excluded unless `--include-archived`.

### Claims
Each bullet is a claim. Bodkin chooses among claims and never rewrites them.
```toml
[[claims]]
id = "crash-safety"
group = "durability"          # at most one bullet per group is used until groups run out
text = 'Event-sourced with a CRC-framed WAL: **0** acked commands lost in **1,000** SIGKILL runs.'
numbers = ["0", "1,000"]      # EVERY number in any text of this claim must be declared here
skills = { wal = 1.0 }        # optional: overrides the item's skills for this bullet
[claims.variants]             # optional alternative wordings, keyed by archetype
fintech = 'Guaranteed no acknowledged order is lost or double-booked: ...'
[claims.proof]
status = "proven"            # proven | reported | pending
command = "make crash-test"  # how to reproduce it (required for proven)
artifact = "bench/results/crashtest-*.json"   # file (glob) in the item's repo (required for proven)
date = "2026-11-10"
limits = "Process crash only, not power loss."   # shown whenever this bullet is used
note = "Where a reported number comes from."
```
- `**bold**` becomes bold in Markdown and `\textbf{}` in LaTeX.
- Use single-quoted TOML strings so quotes inside texts need no escaping.

### Proof status
| status | meaning | used in output? |
|---|---|---|
| `proven` | a command and a result file in the project repo back it, and someone re-ran it | yes |
| `reported` | from your resume or a README, not re-run when the bank was written | yes, shown as "reported (re-verify)" |
| `pending` | not yet true or not yet measured | **never**, unless `--include-pending` (for what-if only) |

### What `validate` enforces
Numbers in any text must be declared (so a bullet cannot drift from its evidence); banned wording (`data/lint.toml`: "fault-tolerant", "production-grade", "exchange-grade", "highly available", ...) unless the claim lists it in `allow`; length (warn above 130 characters, about one resume line); skill and archetype ids must exist; a `proven` claim needs a command and an artifact; proof dates older than 120 days warn.

## roadmap.toml
Planned projects with `skills` and `archetypes`. For each JD skill with no evidence in the bank, the report names the planned projects whose skills would close the gap. Move a project into `items/` (with proven claims) when it is built.

## data/skills.toml
The taxonomy: about 140 skills with aliases and archetype weights. Add skills and aliases freely; `./bodkin taxonomy` checks it. The report lists terms from a JD that the taxonomy did not recognise so you can see what to add.
