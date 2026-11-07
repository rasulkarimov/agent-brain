# agentBrain — plan

**Problem.** Agents forget between sessions, and people pay for it. A conversation remembers itself only while its session lives; between sessions the only memory is what happened to land in a system (a ticket comment, a merge request). A colleague, another agent or a new conversation starts from zero, and a handover is a retelling in chat. Each team that builds agents builds its own partial memory, inside one harness, invisible to the others.

**Goal.** One thin, governed memory layer that every agent and every platform reads and writes through MCP: notes with an author, a scope and versions, audited, readable by the next session or the next person, on the company's own infrastructure. A handover is a note.

The layer stores facts and decisions about the work. Procedures stay skills; the record of who did what to which system stays the platform's audit log.

## Model

A **note** is a short Markdown document:

| Field | Meaning |
|---|---|
| `id`, `version` | every write makes a new immutable version; the latest is current |
| `scope` | `user:<id>`, `team:<group>`, `system:<name>` (a cluster, a project, a pipeline), `ticket:<system>/<id>` |
| `path` | a readable name inside the scope, e.g. `incidents/2026-11-07-spark-oom.md`; the name says what the note is about |
| `kind` | `finding` · `decision` · `handover` · `runbook-gap` · `event` |
| `author` | the user and, when an agent or a platform wrote it, the session or run |
| `links` | runs, tickets, merge requests, approvals it refers to |
| `body` | Markdown, size-capped; secrets refused on write |

Scopes follow Keycloak: a user reads their own scope, the teams they are in, and the `system:` / `ticket:` scopes a policy grants them. Nothing is global by default.

## Tools (MCP)

| Tool | Who | What it does |
|---|---|---|
| `brain_tree(scope?)` | agents | paths and one-line summaries the caller can read — the entry point, not the bodies |
| `brain_read(scope, path, version?)` | agents | one note |
| `brain_search(query, scope?)` | agents | notes by text, newest first |
| `brain_write(scope, path, kind, body, links?, base_version?)` | agents | a new version; `base_version` makes a concurrent edit fail instead of overwriting |
| `brain_handover(to, ticket?, body, links?)` | agents, on a person's request | a `handover` note in the receiver's scope and a notice to them |
| `brain_event(scope, kind, payload, links)` | platforms (service account) | a deterministic `event` note: an approval decided, a merge request opened, a run finished |

Every call is in the audit log with the caller, the session and the client.

## When notes are written

The most reliable notes are not written by the model.

**1. The platform, deterministically** (`brain_event`, no model involved):
- an approval decided — what was proposed, who approved or denied, and the comment; a denial with a reason keeps the next run from repeating the mistake;
- an external artifact created — merge request, ticket comment, secret path — linked to its ticket and system;
- a run finished — status, systems touched, links, taken from the audit log rather than from the model's memory.

**2. The agent, at set moments** — named in the harness's `AGENTS.md` and, more precisely, as steps inside skills:
- an investigation reached a conclusion → `finding`, before answering the person;
- the person chose an option in the conversation → `decision` with the reason;
- a skill did not cover the situation → `runbook-gap`; these feed skill improvements;
- a skill's own step, e.g. "record the plan as a decision" after planning a deployment.

**3. A person, explicitly:** "remember that…" in the conversation; a handover only on a person's command — an agent never hands over on its own.

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
- **Storage:** Postgres, `notes` (one row per version) and `audit_log`; the service's role may insert, not update or delete. Rollback is a new version equal to an old one. Text search in Postgres first; embeddings only if search proves weak, and then with a local model.
- **Sign-in:** Keycloak OAuth 2.1 (PKCE) for clients; the token's audience is agentBrain only and is never forwarded. Platforms use a service account limited to `brain_event`.
- **Console:** tree by scope, versions with diffs, who wrote what in which session, handovers waiting, notes not read for long.
- **Deployment:** one Helm chart, no GPU, about one CPU and a Postgres; on a client site everything stays local.

## Phases

| Week | Scope | Done when |
|---|---|---|
| 1 | repo, schema, MCP server with tree / read / write / search, versions, `user:` and `ticket:` scopes, Keycloak sign-in | a note written from Claude Code or Codex is found by a new session |
| 2 | `brain_event` from AgentGate (approvals, merge requests, finished runs); one line in AgentGate's runner `AGENTS.md`; read-only console | a new conversation on a ticket continues where the last one stopped, without being told |
| 3 | `brain_handover` with a notice; `team:` scopes from Keycloak groups; rollback in the console | an on-call engineer hands an investigation to a colleague in one step and the colleague's session continues from it |
| 4 | bench: 4–6 two-step scenarios run with and without memory; demo video | a number: with memory X of N solved, without Y of N, unsafe 0 |

## Measures

- Follow-up sessions on a ticket that read an earlier note, and how many of them succeeded.
- Two-step bench scenarios solved with memory vs without.
- Time from handover to the receiver's first useful action.
- Notes written vs read: a note never read is a cost, not memory.

## Risks

- **A dump nobody reads:** summaries and dates in the tree, notes not read for a set time marked stale and hidden from the default tree, read counts in the console.
- **Wrong notes steer later sessions:** author and session on every note; supersede and retract; the bench measures sessions with and without memory.
- **Leaking across scopes:** every read checked against the caller's groups; external clients get exactly the user's scopes.
- **Secrets in notes:** redaction on write; a matching note is refused, not stored masked.
- **Prompt injection through notes:** notes are data written by people and agents, marked as such in the tool results; writes to shared scopes carry their author.
- **Seen as a feature of AgentGate:** agentBrain is a separate service with its own API; AgentGate is its first client, not its home.

## Open questions

- Should a handover need the receiver's acceptance, or start a session at once?
- Team scope: Keycloak groups as they are, or a separate team list?
- Ticket comments: keep the agent's plan there for people outside the platform, with the note holding the rest — or let the note replace them?
