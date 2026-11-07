# Business case — external evidence (draft)

Material for `form.md` and `idea.md`, collected from the Telegram channel «LLM под капотом» (Rinat Abdullin, @llm_under_hood) — an author who runs the BitGN agent competitions and builds a shared agent memory ("Company Brain") himself. Post links: `https://t.me/llm_under_hood/<id>`.

**Before using any number in the submission:** these are the author's reports, not peer-reviewed data. Numbers marked *secondary* are his retelling of someone else's talk — check the primary source (the video or article he links) and quote that instead.

## Direction of the market

| Claim | Number | Source | Use for |
|---|---|---|---|
| AI-native companies organise around a central "company brain" — a shared layer of memory and tools — instead of hierarchy; people work as individual contributors / directly responsible owners | — | YC partner talk "Building And Structuring An AI Native Company" (YouTube), via id978, id980 | why a shared memory layer is the core of an AI-native org |
| Companies using this approach reach their first large funding round with far fewer employees | ~80% fewer, *secondary* (YC, via id980) | id980 | impact framing; verify in the YC video |
| A 15-person bootstrapped, profitable product company in DACH outpaces competitors; one reason given is a shared layer that grew from Notion and git vaults into a self-built versioned system | anecdote | id980 | "parallel evolution" — the pattern appears independently |
| Models and harnesses improve monthly; what did not change across a year of agent competitions is the memory-and-tools layer and the patterns of using it — so invest there, not in the agent | — | id985 | the core thesis: memory outlives the harness |
| A large fintech moved its engineers from cloud coding agents to an open model on its own GPUs | ~90% cost saving, delivery speed up, *secondary* (Revolut talk, via id985) | id985 | local models are production-grade; the memory must not be tied to one provider |
| "LLMs are getting so smart that smart agents and complex harnesses will matter less" | — | *secondary* (Lenny's podcast, via id985) | supports harness-agnostic design |

## Evidence that a shared memory works

| What | Number | Source |
|---|---|---|
| Workshop: 20 people with no AI-engineering background connect their own ChatGPT / Claude to one shared memory and organise into an "AI R&D lab" in two hours | agent quality on a benchmark from 7 → 55.47 in 2 h, 70.20 by the next day | id964 |
| Two days of that workshop | 8,650 sandbox runs, 697 changes, 150 experiments, 1.4 GB of data; almost every experiment was the joint work of several agents | id966 |
| Heterogeneous agents through one unfamiliar collaboration interface | errors in 4% of requests for coding agents, 6.5% for chat agents; 94% corrected themselves at once; even free tiers contributed | id967 |
| Open swarm: ~30 different harnesses on one shared memory, writing an e-commerce agent on an open local-class model (gpt-oss-120b) | 46.5% → 78.3 → 95.1, top-10 of the leaderboard | id973, id974, id976 |
| Handover of a prototype between two people through their agents and a shared workspace | 7 manual steps → 4; no special integration; the sending agent left implementation notes for the receiving one on its own | id986 |
| An agent used the shared memory's tools to deliver a result to the right person without being asked | anecdote | id979 |

## Design lessons (use in "why it is different" and "risks")

| Lesson | Source |
|---|---|
| Version the whole memory, not files: an agent's change to a thousand files in several workspaces is rolled back as one; nothing is a black box | id957, id977 |
| Progressive disclosure: an agent sees a short entry point and the tree, reads details on demand; with code-mode interfaces token use for typical tasks dropped ~1000× at Cloudflare's scale (2,549 tools) — *secondary* | id958, id966 |
| A document tree beat "skills" in accuracy for both Claude and Codex, more so as projects grow; Claude truncates skill descriptions past ~1% of the context | id960 |
| Narrow memory interfaces cost model capability; an SDK run next to the data cut a write task from 6.5 to 3.5 min | id845, id957 |
| Instructions: root rules set global limits, nested ones refine their subtree, conflicts are raised, not resolved silently (OpenAI Model Spec levels) | id788 |
| Shared instruction files get filled with noise when anyone can write them | id966 |
| A swarm without explicit quality rules takes shortcuts (hard-coded regexes) — processes and checks must live in the memory | id976 |
| Storage grows faster than expected: 10k documents and 100k versions filled 45 GB and took the system down; content-addressed immutable trees brought 40 GB to 500 MB | id977, id983 |
| A lesson is learned when it changes later decisions or checks; verify by re-running the task that once failed | id940 |
| Reliable agents for business: deterministic control flow + distilled rules + automated validation; the LLM is not the central engine | id719 |
| Keep a separate, durable index of your own sessions; link it from the memory rather than loading it | id984 |

## Where agentBrain differs from the channel's Company Brain

- **Governed for regulated sites:** Keycloak sign-in without token passthrough, workspaces by group, approvals for instruction files, redaction of secrets on write, audit of every call.
- **Platforms write facts deterministically** (`brain_event`): approvals, merge requests, finished runs — the model writes only conclusions.
- **Air-gapped first:** no model inside the memory service; distill runs on the site's own model.
- **Typed tools first,** a server-side sandbox later — easier to review and approve on restricted sites.
