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

Prototype, running on the internal dev cluster next to AgentGate (namespace `agentgate`):

- MCP at `https://agentbrain.intdev.presight.ai/mcp` — clients sign in to Keycloak themselves (OAuth, PKCE, client `agentbrain-mcp`); the token is checked against the realm's keys and the `agentbrain` audience and never passed on.
- Tools: `brain_start`, `brain_tree`, `brain_read` (by section, by version), `brain_search`, `brain_write` (notes and documents), `brain_handover`, `brain_history`.
- Changesets: every session is one change; the console rolls one back as a whole.
- Instructions in the memory: `CORE.md` and workspace `AGENTS.md` returned on start, writable only by an admin in the console.
- Refusals: a write with a secret-looking value, an edit of a note, a document changed since it was read (conflict).
- AgentGate as the first client: its gateway offers the agent `brain_*` on behalf of the run's user (the run is the session), and records every decided approval as an `event` note.
- Console at `https://agentbrain.intdev.presight.ai/` behind oauth2-proxy: tree, documents with history, sessions with rollback, audit.

Not yet: distill, handover notices outside the memory, team workspaces from Keycloak groups beyond the seed, the bench with and without memory.

## Connect

Claude Code (the cluster's certificate is signed by the internal CA: give Node the CA once):

```bash
kubectl -n agentgate get cm ca-bundle -o jsonpath='{.data.ca\.crt}' > ~/.presight-ca.crt
claude mcp add --transport http --client-id agentbrain-mcp --callback-port 33418 agentbrain https://agentbrain.intdev.presight.ai/mcp
NODE_EXTRA_CA_CERTS=~/.presight-ca.crt claude
```

Then `/mcp` → agentbrain → Authenticate signs in through Keycloak in the browser.

Codex (it needs the internal CA next to the public and corporate roots):

```bash
security find-certificate -a -p /Library/Keychains/System.keychain /System/Library/Keychains/SystemRootCertificates.keychain > ~/.presight-ca-bundle.crt
cat ~/.presight-ca.crt >> ~/.presight-ca-bundle.crt
codex mcp add agentbrain --url https://agentbrain.intdev.presight.ai/mcp --oauth-client-id agentbrain-mcp
SSL_CERT_FILE=~/.presight-ca-bundle.crt codex mcp login agentbrain
SSL_CERT_FILE=~/.presight-ca-bundle.crt codex
```

## Run locally

```bash
uv sync && uv run pytest
uv run python -m agentbrain   # dev mode: MCP on :8790 (bearer = user name), console on :8791/?dev_user=<name>
```

## Deploy

```bash
python3 deploy/setup.py              # Keycloak clients, database, Secret agentbrain (once)
helm upgrade --install agentbrain ./helm -n agentgate -f helm/values-dev.yaml --set image.tag=<tag>
```

## Documents

- [docs/plan.md](docs/plan.md) — model, tools, when notes are written, phases, risks
- [form.md](form.md), [idea.md](idea.md) — Eureka 3.0 drafts
- [docs/business-case-sources.md](docs/business-case-sources.md) — external evidence for the business case, with sources
