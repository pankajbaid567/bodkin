# Bodkin report: Software Engineering Intern 2027 (India)

Every bullet below is verbatim text from your bank; Bodkin selected and ordered, it wrote nothing. `proven` = backed by a proof command and result file; `reported` = from your resume or a README, re-verify.

## 1. What the JD is about

- `backend    ` ██████████ 1.00
- `genai      ` █████████░ 0.94
- `devtools   ` ██████░░░░ 0.57
- `ml         ` ██████░░░░ 0.56
- `systems    ` █████░░░░░ 0.54
- `lowlatency ` █████░░░░░ 0.49

Top skills (weight, where it was said):

- **Data structures & algorithms** 1.00 (2x, required): Strong foundation in data structures and algorithms.
- **Code review** 0.84 (2x, responsibilities): Write clean, tested code and take part in code reviews.
- **C++** 0.80 (1x, required): Proficiency in Java, Python, C or C++.
- **Java** 0.80 (1x, required): Proficiency in Java, Python, C or C++.
- **Python** 0.80 (1x, required): Proficiency in Java, Python, C or C++.
- **AI agents** 0.40 (1x, preferred): Exposure to AI/ML, including MCP and agentic AI.
- **GenAI** 0.40 (1x, preferred): Exposure to AI/ML, including MCP and agentic AI.
- **MCP** 0.40 (1x, preferred): Exposure to AI/ML, including MCP and agentic AI.
- **Machine learning** 0.40 (1x, preferred): Exposure to AI/ML, including MCP and agentic AI.
- **System design** 0.40 (1x, preferred): Basic system design knowledge.

Eligibility (advice; extracted from free text, check the JD yourself):

- OK  **CGPA**: JD asks 6+ ('CGPA of 6+'); you have 8.618
- OK  **Batch**: JD targets 2028; your batch is 2028

## 2. Recommended projects (top 3)

### 1. Pitbook – Crash-safe matching engine and live order book  (November 2026) 

[github](https://github.com/pankajbaid567/pitbook) · [demo](https://pitbook.baidpankaj567.workers.dev)

Covers 23% of this JD's weighted need. Why: Data structures & algorithms (0.50); backend (role type) (0.48); systems (role type) (0.33); System design (0.28); lowlatency (role type) (0.24)

- Designed a Go engine whose state is a pure function of its log; matched a reference model over **1,000,000** random commands.  _[proven, backend variant]_
- Proved the tests have teeth: **5 of 5** deliberately injected engine bugs are caught by the property test.  _[proven]_
- Made order entry crash-safe: **0** acknowledged commands lost or duplicated across **1,000** SIGKILL runs (**117,609** acks checked).  _[proven, backend variant]_
- Open-loop benchmarks (Apple M3): **137 ns**/command core, **~670k**/s engine-only, **~80k**/s with fsync before every ack.  _[proven]_

### 2. Cairn – Permission-aware evidence search and decision memory  (November 2026) **[WIP]**

Covers 14% of this JD's weighted need. Why: Python (0.39); genai (role type) (0.28); MCP (0.20); GenAI (0.18); AI agents (0.14)

- Shipped an MCP stdio server with per-agent tokens and ACL-first GitHub sync; revocations answer **503** until applied.  _[reported (re-verify)]_
- Postgres row-level security plus per-query checks; **50** canary tests find **0** leaks across **5** MCP tools and **2** agents.  _[reported (re-verify)]_
- Built permission-aware evidence search: answers cite only documents the asker may read, else say "not found".  _[reported (re-verify)]_
- Verified generated answers: unsupported claims are dropped; if nothing survives, the reply is a fixed not-found message.  _[reported (re-verify)]_

### 3. cache-cluster – Sharded in-memory cache with W-TinyLFU in Go  (November 2026) **[WIP]**

Covers 3% of this JD's weighted need. Why: Data structures & algorithms (0.17); distributed (role type) (0.06); lowlatency (role type) (0.02); backend (role type) (0.02); systems (role type) (0.02)

- Built a sharded Go cache: W-TinyLFU eviction, consistent-hash client ring, singleflight stampede protection, RESP2-subset server.  _[reported (re-verify)]_
- Evaluated policies on real Twitter traces: W-TinyLFU beat LRU by up to **11.5** hit-ratio points and lost once, at the smallest size.  _[reported (re-verify)]_
- Cross-checked the LRU simulator against libCacheSim on **3** traces x **3** sizes: max hit-ratio difference **0.00004**.  _[reported (re-verify)]_
- Verified under the Go race detector with a fuzzed RESP parser and nightly stress runs in CI.  _[reported (re-verify)]_

## 3. Experience (bullets ordered for this JD)

### Founding Software Engineer (AI & Backend), in.culcate  (September 2024 - March 2026)

- Engineered a **5+** agent pipeline (scripting, voice, ElevenLabs narration), cutting production time **40%**.  _[reported (re-verify)]_
- Built **20+** REST endpoints in Node.js, Express.js, MongoDB for auth and content in a **2,000**-user app.  _[reported (re-verify)]_
- Streamlined the team's deployment workflow, running backend services on **AWS EC2**.  _[reported (re-verify)]_
- Automated **5+** publishing workflows with a centralized CMS, reducing content turnaround time by **30%**.  _[reported (re-verify)]_

## 4. Achievements

- Merged a fix to Hugging Face Transformers (**168k**-star repo, PR #42373): TensorDict padding regression.  _[reported (re-verify)]_
- Team rank **8** on the public leaderboard among ~**80,000** registered participants, Amazon ML Challenge 2026.  _[reported (re-verify)]_
- CodeChef 3-star (rating **1638**); **600+** DSA problems solved across platforms.  _[reported (re-verify)]_

## 5. Skills section (re-ordered; **bold** = the JD mentions it)

- **Databases & Data Tools:** MySQL, MongoDB, PostgreSQL
- **Frameworks & Libraries:** Tailwind, Next JS, React Native, Prisma ORM, React, Redux, Node.js, Express JS, FastAPI
- **Computer Language:** **Python**, **C++**, JavaScript, TypeScript, SQL
- **Generative AI & LLMs:** **GenAI**, RAG, LangChain, LangGraph, LLM, Hugging Face

## 6. Gaps and coverage

JD skill coverage (profile skills + chosen items): **67%**
Not covered: Code review, Java, Machine learning

You have used these (the bank shows it) but your skills line does not list them. Add them if true:

- **Data structures & algorithms** (JD weight 1.00): evidence in codechef
- **Code review** (JD weight 0.84): evidence in ell-ena, hf-pr
- **AI agents** (JD weight 0.40): evidence in cairn, incalculate
- **MCP** (JD weight 0.40): evidence in cairn
- **Machine learning** (JD weight 0.40): evidence in amazon-ml
- **System design** (JD weight 0.40): evidence in pitbook

No proven evidence anywhere in the bank:

- **Java** (JD weight 0.80): would be closed by: Concurrency lab

Listed in your skills but no project demonstrates them: C++

## 7. Ranking of all projects (stand-alone relevance)

| project | relevance | quality | used |
|---|---|---|---|
| Pitbook | 2.11 | 1.00 | yes |
| Cairn | 1.49 | 0.49 | yes |
| VITRAM | 1.08 | 0.70 |  |
| cache-cluster | 0.76 | 0.49 | yes |
| Resilient TaskFlow | 0.52 | 0.70 |  |

## 8. Read before you use this

- Cairn is WIP: WIP: built and tested locally but not deployed or published, and only a fake-model evaluation has been run (real-model quality unmeasured). Name has collisions; rename decision is open. Numbers are from the project README, not re-run by Bodkin's author.
- Cairn: 4 of 4 bullets are 'reported' (from your resume or a README, not re-run by the bank's author); re-verify before an interview
- cache-cluster is WIP: WIP: complete locally but the repo has no git commit or public link yet. Numbers are from its BENCHMARKS.md and DESIGN.md, not re-run by Bodkin's author. It is a sharded cache, not a fault-tolerant database: no replication or persistence.
- cache-cluster: 4 of 4 bullets are 'reported' (from your resume or a README, not re-run by the bank's author); re-verify before an interview
- limit (pitbook/reference-model): Simulator: one venue, no real money.
- limit (pitbook/crash-safety): Process crash (SIGKILL) only; the OS page cache survives, so power loss is not tested.
- limit (pitbook/performance): One busy laptop; tail latencies at 100k/s and above are dominated by scheduler noise (see BENCHMARKS.md control).
- limit (cairn/rls-canary): Synthetic data; not an externally audited security product.
- limit (cairn/verified-answers): The verifier is lexical: it can pass a claim that rearranges true words into a false meaning.
- limit (cache-cluster/design): No replication, no persistence, static membership.
- limit (cache-cluster/traces): Prefixes of the traces, cold-start misses included.
