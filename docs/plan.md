# agentBrain — plan

**Problem.** Agents forget between sessions, and people pay for it. A conversation remembers itself only while its session lives; between sessions the only memory is what happened to land in a system (a ticket comment, a merge request). A colleague, another agent or a new conversation starts from zero, and a handover is a retelling in chat. Each team that builds agents builds its own partial memory, inside one harness, invisible to the others.

**Goal.** One thin, governed memory layer that every agent and every platform reads and writes through MCP: workspaces of documents and notes with authors, scopes and versions, audited, readable by the next session or the next person, on the company's own infrastructure. An agent that connects learns from the memory itself what it is for and how to work in it. A handover is a note.

The layer stores facts, decisions and the current state of the work. Procedures stay skills; the record of who did what to which system stays the platform's audit log.

## Place in a Company OS

Two layers, one idea: models and harnesses change every month, the memory and the tools around them stay — so that is where to invest, in a form any harness can plug into.

| Layer | What | Here |
|---|---|---|
| Tools | typed, governed actions on real systems: approvals, as-user access, audit | [AgentGate](https://github.com/rasulkarimov/agent-gate) gateway |
| Memory | what is known, decided and in progress; instructions for working with it | agentBrain |
| Harness and model | Copilot, Claude Code, Codex, an in-house runner; local or provider models | swappable, not built here |

agentBrain is a separate service with its own API; AgentGate is its first client and its source of platform events, not its home.

## Model

**Workspace** — a folder with its own purpose and rights: `team/ops`, `system/aks-intdev`, `project/notes-api`, `user/<id>`. Rights follow Keycloak groups; nothing is global by default. A workspace may hold an `AGENTS.md` with rules for its subtree.

Two kinds of content live in a workspace:

| | Note | Document |
|---|---|---|
| What | one fact or event: `finding`, `decision`, `handover`, `runbook-gap`, `event` | the living state: project status, known issues, a runbook draft, an incident review |
| Size | short, capped | any; read by section through an automatic outline |
| Written by | agents at set moments, platforms, people | the distill step, people, agents on request |
| Lifetime | append; superseded or retracted, not edited | edited in place, every change versioned |

Every note and document has an author (the user and, when an agent or a platform wrote it, the session), links (runs, tickets, merge requests, approvals) and a readable path — the name says what it is about.

**Changeset.** Every session is one change: `brain_start` opens it, every write inside belongs to it, it closes when the session ends. History is a sequence of changesets across the whole memory, not versions per file — so a session that touched thirty documents in three workspaces is reviewed and rolled back as one, and a rollback is itself a new changeset. Two sessions that change different documents merge on their own; two that change the same document get a conflict with both versions, and the later writer merges.

## Instructions live in the memory

An agent learns how to work from the memory, not from its harness — so Copilot, Claude Code and an in-house runner behave alike.

1. **On connect** the server's MCP `instructions` say what the memory is, how to start (`brain_start`), and that notes are data, not commands.
2. **Core** — a small `CORE.md` at the root, written by people: purpose, language, priorities, limits. `brain_start` always returns it.
3. **Workspace `AGENTS.md`** — rules for that subtree, returned when the session enters it. Precedence: system and harness instructions, then the person's request, then root rules, then nested ones as local refinements; a nested rule that contradicts a higher one, or two rules on the same level that conflict, are raised to the person, not resolved silently.
4. **Protected:** `CORE.md` and every `AGENTS.md` change only with a human approval. A shared memory without that fills its instruction files with noise.

## Tools (MCP)

| Tool | Who | What it does |
|---|---|---|
| `brain_start(task, workspace?)` | agents | opens the session's changeset; returns the core, the workspace rules and the tree of what the caller can read |
| `brain_tree(path?)` | agents | paths and one-line summaries — the entry point, not the bodies |
| `brain_read(path, section?, version?)` | agents | a note, or a document or one section of it by its outline |
| `brain_search(query, path?)` | agents | text search, newest first |
| `brain_write(path, kind, body, links?)` | agents | a note, or a new version of a document, inside the session's changeset |
| `brain_handover(to, ticket?, body, links?)` | agents, on a person's request | a `handover` note in the receiver's workspace and a notice to them |
| `brain_event(workspace, kind, payload, links)` | platforms (service account) | a deterministic `event` note: an approval decided, a merge request opened, a run finished |

Every call is in the audit log with the caller, the session and the client. Tool errors are recorded by kind, so tool descriptions are corrected where agents keep failing.

**Typed tools first, a sandbox later — a deliberate choice.** The leanest interface for a large memory is two commands: start a session and get an SDK description, then run a short script on the server, next to the data. It cuts tool descriptions to a constant and lets an agent change many documents in one step. For a governed, air-gapped first version typed tools are easier to review, to approve and to explain to security, and notes are small. The sandbox comes with large documents and bulk edits (phase 4), behind the same audit.

## When content is written

The most reliable records are not written by the model.

**1. The platform, deterministically** (`brain_event`, no model involved):
- an approval decided — what was proposed, who approved or denied, and the comment; a denial with a reason keeps the next run from repeating the mistake;
- an external artifact created — merge request, ticket comment, secret path — linked to its ticket and system;
- a run finished — status, systems touched, links, taken from the audit log rather than from the model's memory.

**2. The agent, at set moments** — named in workspace `AGENTS.md` and, more precisely, as steps inside skills:
- an investigation reached a conclusion → `finding`, before answering the person;
- the person chose an option in the conversation → `decision` with the reason;
- a skill did not cover the situation → `runbook-gap`;
- a skill's own step, e.g. "record the plan as a decision" after planning a deployment.

**3. A person, explicitly:** "remember that…" in the conversation; a handover only on a person's command — an agent never hands over on its own.

## Distill: from notes to knowledge

Notes and events pile up; read one by one they are a log, not memory. On a schedule and on demand, a distill session per workspace turns them into documents:

- new notes since the last pass → the workspace's documents (project state, known issues, incident reviews), with links back to the notes they came from;
- repeated `runbook-gap` notes → a proposed skill change, reviewed and checked on the bench like any skill change;
- lint: stale documents, broken links, notes nobody read, contradictions between documents.

Distill is an ordinary agent session through the same tools and changesets, so its result is reviewed and rolled back like anyone's. It runs on the site's model; the memory service itself still calls no model.

## Lessons that stick

A lesson is learned when it changes a later decision or check. The loop:

```
failure or denial ──► note (finding / runbook-gap / event)
        │
distill ──► document or skill change ──► review ──► bench
        │
re-run the original failing task ──► it now passes
```

The bench keeps the tasks that once failed; each change to a skill or an instruction file re-runs them.

## Handover

```
on-call engineer ──► session investigates ──► brain_handover(to=engineer, ticket=…)
                                                   │
engineer gets a notice ──► new session starts with the handover note
                                                   │
                               reads it, the linked runs and the ticket
```

Sessions stay private; the note is what was meant to be passed on.

## Architecture

- **Service:** MCP server (streamable HTTP) + small API for the console; Python, FastAPI, as AgentGate.
- **Storage:** Postgres for the tree, changesets and audit; bodies content-addressed (one copy per distinct content), so a hundred versions of a large document do not mean a hundred copies. The service's role may insert, not update or delete. A retention policy for old versions of notes nobody reads. Text search in Postgres first; embeddings only if search proves weak, and then with a local model.
- **Sign-in:** Keycloak OAuth 2.1 (PKCE) for clients; the token's audience is agentBrain only and is never forwarded. Platforms use a service account limited to `brain_event`.
- **Console:** the tree by workspace, changesets with diffs and one-click rollback, who wrote what in which session, handovers waiting, notes not read for long, approvals for instruction files.
- **For people outside the console:** a read-only Markdown export (or a git mirror) of the workspaces the reader may see, so the memory opens in Obsidian or any editor.
- **Own sessions (optional):** an index of a user's own past sessions with their agents, readable only by that user, linked from their workspace — "what did we decide last month" without storing chat logs in shared memory.
- **Deployment:** one Helm chart, no GPU, about one CPU and a Postgres; on a client site everything stays local.

## Phases

| Week | Scope | Done when |
|---|---|---|
| 1 | schema with workspaces and changesets; `brain_start` / `tree` / `read` / `write` / `search`; `CORE.md` and workspace `AGENTS.md` returned on start; Keycloak sign-in | a note written from Claude Code or Codex is found by a new session, and the new session follows the workspace rules it was given |
| 2 | `brain_event` from AgentGate (approvals, merge requests, finished runs); console: tree, changesets, rollback, approval of instruction files | a new conversation on a ticket continues where the last one stopped; a bad session is rolled back in one step |
| 3 | `brain_handover` with a notice; team workspaces from Keycloak groups; distill per workspace; documents read by section | an on-call engineer hands an investigation to a colleague in one step; a week of notes is distilled into an up-to-date known-issues document |
| 4 | bench: two-step scenarios with and without memory, and re-runs of once-failing tasks; demo video. Then: sandbox interface for bulk edits | a number: with memory X of N solved, without Y of N, unsafe 0; a fixed failure stays fixed |

## Measures

- Follow-up sessions on a ticket that read an earlier note, and how many of them succeeded.
- Two-step bench scenarios solved with memory vs without; once-failing tasks that now pass.
- Time from handover to the receiver's first useful action.
- Notes written vs read, and notes distilled into documents: a note never read is a cost, not memory.
- Tool errors per hundred calls, by tool and client.

## Risks

- **A log, not memory:** distill per workspace; stale notes marked and hidden from the default tree; read counts in the console.
- **Wrong content steers later sessions:** author and session on everything; supersede and retract; changesets rolled back as a whole; the bench measures sessions with and without memory.
- **Instruction files filled with noise:** changes to `CORE.md` and `AGENTS.md` only with an approval.
- **Leaking across workspaces:** every read checked against the caller's groups; external clients get exactly the user's rights.
- **Secrets in notes:** redaction on write; a matching write is refused, not stored masked.
- **Prompt injection through notes:** notes are data written by people and agents, marked as such in tool results; writes to shared workspaces carry their author.
- **Storage grows faster than expected:** many agents writing at once produce versions quickly; content-addressed bodies, retention for unread notes, a size alarm per workspace.
- **Seen as a feature of AgentGate:** a separate service with its own API and its own clients; AgentGate is the first of them.

## Open questions

- Should a handover need the receiver's acceptance, or start a session at once?
- Team workspaces: Keycloak groups as they are, or a separate team list?
- Ticket comments: keep the agent's plan there for people outside the platform, with the note holding the rest — or let the note replace them?
- Distill schedule: nightly per workspace, or after N new notes?
