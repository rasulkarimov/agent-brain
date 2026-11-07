# agentBrain

**Sovereign shared memory for AI agents.** Any agent — GitHub Copilot, Claude Code, Codex, an in-house runner — reads and writes one memory over MCP. Every note is versioned, has an author and a scope, is audited, and stays inside the perimeter. The memory itself runs no model.

## Why

What an agent learns in one session is lost to the next. A second engineer, another agent or the same engineer in a new conversation starts from zero: the findings, the decision and its reason, what was already tried. Handing work over means retelling it.

Models and harnesses change every month; the memory and the tools around them stay. So the durable investment is the memory layer, not the agent — and any harness should be able to plug into it.

## What it does

- **Workspaces of documents and notes, not chat logs.** Living documents (project state, known issues, runbooks) and short notes — `finding`, `decision`, `handover`, `runbook-gap`, `event` — with author, links and rights per workspace.
- **One session, one change.** Every session is a changeset across the whole memory: reviewed and rolled back as one, however many documents it touched.
- **Instructions in the memory.** On connect an agent gets the core (purpose, priorities, limits) and the rules of the workspace it enters — the same for every harness. Instruction files change only with an approval.
- **Progressive disclosure.** An agent starts with the tree (paths and one-line summaries) and reads bodies or single sections on demand, so the prompt does not grow with the memory.
- **Distill.** Notes are turned into documents per workspace on a schedule; repeated gaps become proposed skill changes, checked on the bench.
- **The platform writes facts, the agent writes conclusions.** Approvals, merge requests and finished runs are recorded by the platforms that see them (`brain_event`), deterministically; the model writes only findings and decisions, at set moments.
- **Handover in one step.** `brain_handover` puts a note in a colleague's scope; their next session starts from it.
- **Governed.** Keycloak sign-in (OAuth, no token passthrough), scopes from groups, append-only versions, rollback, redaction of secrets on write, every call in the audit log.

## Status

Planning. First client: [AgentGate](https://github.com/rasulkarimov/agent-gate) — its runner and gateway use agentBrain for memory between runs and for handovers.

## Documents

- [docs/plan.md](docs/plan.md) — model, tools, when notes are written, phases, risks
