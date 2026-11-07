# Eureka 3.0 — form fields

## 1. Theme
Sovereign & Responsible AI
*(alternative: Agentic AI for Mission-Critical Ops — if positioned as on-call handover and incident memory; Future of Work is excluded from the golden ticket and is a worse fit)*

## 2. Problem

**Idea title** (≤140)
agentBrain: AI Agents That Remember — Governed Shared Memory Inside the Perimeter
*(alternatives: "agentBrain: One Governed Memory for Every AI Agent, on Air-Gapped Sites" · "Stop Agents Forgetting: Sovereign Shared Memory for Teams and Their Agents")*

**One-line summary**
agentBrain gives every AI agent a team uses — GitHub Copilot, an in-house agent, a local model on an air-gapped site — one shared, governed memory: findings, decisions and handovers survive the session, every change is versioned and can be rolled back, and nothing leaves the perimeter. Working today on Presight's internal cluster: an engineer's Claude Code and AgentGate's on-prem agent share one memory, and a new investigation picks up where earlier ones stopped — without being told.

**What problem are you solving?**
AI agents forget. What an agent finds in one session — why a job failed, which fix was rejected and why, what the person decided — is gone when the session ends. The next session, a colleague's agent or the engineer on the next shift starts from zero: the same investigation is repeated, a fix that was already denied is proposed again, and a handover is a retelling in chat. Each tool keeps its own partial memory, locked inside one vendor's assistant and invisible to the others.

On mission-critical and air-gapped sites this is worse. Cloud assistants with built-in memory cannot run there at all, and where agents do run, nothing controls what they remember: no rights on who reads what, no audit of what an agent wrote, no way to undo a bad change, and a real risk of secrets or client data ending up in a memory nobody reviews.

Presight's clients are about to meet this at scale. Abu Dhabi aims to be the world's first fully AI-native government by 2027 (Digital Strategy 2025–2027, AED 13 billion, 200+ AI solutions, sovereign cloud across operations), and in April 2026 the UAE government set out to move 50% of government sectors and services to agentic AI within two years. Abu Dhabi requires every AI system to run within frameworks that define ownership, oversight and monitoring; how an entity shows what its agents knew, who decided and why, and how a wrong step is undone — across many agents from different vendors, each forgetting between sessions — is left to each entity.

We see it in our own work. In AgentGate, where Presight engineers run agents on real operations, one engineer worked on one failing Airflow job for three days in a single AgentGate conversation of 19 messages — "running as expected?", "why did the first try fail?", "why has this failed?". Everything the agent found — the driver running out of memory, the fix, the next failure — lived only in that conversation: a colleague, a new conversation or another assistant could not see it, and when the conversation ends it is gone. How much time this costs across TechOps (10 engineers) and Data Engineering (14) is the pilot's first measurement: a one-week time log and the share of agent conversations that re-investigate a subject already investigated. Business owner: Atul Vishwakarma, Director – Technical Operations.

## 3. Solution

**Your AI solution**
agentBrain is a thin memory service that any agent reads and writes through the standard Model Context Protocol (MCP): GitHub Copilot in VS Code, an in-house runner, other approved assistants. It runs no model of its own, so it works on sites that cannot call out.

- **Workspaces of documents and notes.** Per team, system, project or person: living documents (project state, known issues, runbook drafts) and short notes — finding, decision, handover, runbook gap, event — each with an author, links to tickets and changes, and rights from the company's sign-in.
- **The platform records facts, the model records conclusions.** Approvals, merge requests and finished runs are written by the platforms that see them, deterministically; the agent writes only its findings and decisions, at set moments in its procedures.
- **One session, one change.** Every session is one versioned change across the whole memory: reviewed in the console and rolled back as one, however many documents it touched.
- **Instructions in the memory.** On connect, any agent gets the same core rules and the rules of the workspace it enters; instruction files change only with a person's approval.
- **Progressive disclosure.** An agent starts from a short tree and reads only what it needs, so the cost per task does not grow with the memory.
- **Handover in one step.** "Hand this investigation to the next shift" puts a handover note in the receiver's workspace; their next session starts from it.
- **Distill.** Notes are regularly turned into up-to-date documents; repeated gaps become proposed procedure changes, checked before they ship.
- **Governed.** Corporate sign-in (Keycloak with Entra ID), workspace rights by group, the client's token never forwarded, secrets refused on write, every call audited.

Working today, on the internal dev Kubernetes cluster next to AgentGate:
- **Any assistant, one memory.** Claude Code on an engineer's laptop connects with one command and signs in through the corporate Keycloak in the browser; AgentGate's on-prem agent (Qwen3.8 27B) uses the same memory on behalf of the user who started the run. No token is copied or forwarded.
- **It works without being told.** Asked only "this job failed again — what's going on?", AgentGate's local model opened the memory first, took the open question from an earlier note as its starting point, found the next cause in the logs, said the earlier cause was already fixed instead of re-investigating it, and wrote its finding back for the next session. Claude Code then read that finding and recorded the team's decision.
- **Facts from the platform:** an approval denied in AgentGate appeared in the memory seconds later with who decided and why, written by the gateway, not by the model.
- **Guardrails, tested:** a note with a secret is refused ("say where the secret lives instead"); an agent rewriting the shared rules is refused; notes are never edited; a document changed since it was read is a conflict, not an overwrite.
- **One session, one change:** any session is rolled back in one click.
- **Handover:** a note in the colleague's own workspace, shown at the start of their next session, once.
- **Console:** a graph of notes and what they link (jobs, runs, branches, tickets), each note with its author, the assistant that wrote it, backlinks and history; a timeline; sessions with rollback; the audit of every call by every client.

Planned: distill (notes into up-to-date documents, repeated gaps into procedure changes), team workspaces from directory groups, the bench with and without memory, GitHub Copilot connected the same way.

agentBrain is a separate service with its own API and its own clients: AgentGate is its first client, an engineer's Claude Code the second. This submission is the memory, not AgentGate's governed gateway — they work together, and each stands alone.

What is new: memory as a governed company asset, independent of the agent. Models and assistants change every month; the memory stays, and any approved assistant plugs into it. On restricted sites it is the only way to give agents memory at all.

In line with Presight's AI use policy: agentBrain does not compete with Microsoft 365 Copilot or GitHub Copilot; it gives them — and local agents where no cloud is allowed — one governed memory that stays inside Presight's or the client's perimeter.

**Technology readiness level**
TRL 5 — a working prototype on the internal dev cluster, integrated with AgentGate and the corporate sign-in, tested end to end with Claude Code and the on-prem model on a real investigation. Not yet in daily team use.

**Tags**
agentic-ai, memory, knowledge-management, sovereign-ai, on-prem, air-gapped, governance, audit, mcp, human-in-the-loop, handover

## 4. Documents
- Idea document: `agentBrain_idea.pdf`, built from `idea.md` with screenshots from the console
- Pitch deck: not attached at submission; the idea document carries the case (a deck follows if shortlisted)

## 5. Prototype
**Type:** Prototype
**Live demo URL:** https://agentbrain.intdev.presight.ai/ — reachable on Azure VPN, or request access through Zscaler
**Repository:** private; walkthrough on request
**Screenshots** (from the real console, real notes):
1. `ab-01-graph.png` — the memory as a graph: notes around one failing job, written by AgentGate's agent and by Claude Code, and the runs, branch and job they link; a note open on the side with its author, assistant and backlinks.
2. `ab-02-timeline.png` — what the memory learned, in order, and through which assistant.
3. `ab-03-sessions.png` — sessions; any one rolled back in one click.
4. `ab-04-audit.png` — every call by every client, including the refused writes (a secret, the shared rules).

**How to test it**
1. Connect Claude Code (one command, shown in the console's README) and sign in with your Presight account in the browser.
2. Ask it: "Start an agentBrain session about spark_landing_to_bronze_streaming — what does the team already know?" It returns what AgentGate's agent and colleagues recorded.
3. Ask it to record a decision; open https://agentbrain.intdev.presight.ai/ and find it in the graph, with its author and the assistant that wrote it.
4. Ask it to save a password: the memory refuses it.

No client data, internal hostnames or credentials appear in any material.

## 6. Impact & team

**Expected impact**
- Fewer repeated investigations: the share of follow-up conversations that start from an earlier note instead of from zero — measured from the audit log in the pilot, with the hours from a one-week time log before and after.
- Faster handover: time from a handover to the receiver's first useful action, before and after.
- Fewer repeated mistakes: an approval denied with a reason is remembered — the bench measures how many follow-up runs avoid the denied action.
- Measured, not claimed: two-step bench tasks solved with memory vs without; once-failing tasks that stay fixed after a procedure change.
- Lean: no GPU for the service — one small container (requests: 0.05 CPU, 128 MB) and a database; the distill step runs on the site's existing model.
- Control: every write to the memory authored and audited (100%); rollback of any session's change in one step; instruction files changed only with approval.
- Client offer — three ways:
  1. Government and regulated entities running agent programmes (Abu Dhabi's AI-native government by 2027, the federal target of 50% of services on agentic AI within two years): the memory layer for their agents, whatever the vendor or model, in their own sovereign cloud or on premises, answering the ownership, oversight and monitoring their frameworks require — author and assistant on every note, audit of every call, rollback of any session.
  2. Inside Presight's AI products where analysts and investigators work with agents: the memory of a case with rights per case, audit and rollback — a direction to validate with the product teams.
  3. Engineering teams on client sites, Presight's or the client's own: what a site learns stays on that site and survives shift changes.
  Next step: a one-to-one review with Solutions and Smart Cities, and one client entity's agent team as design partner for the pilot.
- Reuse: any team with agents — operations, data engineering, delivery, client engineering teams — by adding workspaces, not code.
- Direction of the market: AI-native companies are organised around a shared "company brain" of memory and tools (Y Combinator talk "Building And Structuring An AI Native Company"); this is that layer, built for regulated sites.

**Submitting as:** Individual
**Department / function:** Technical Operations (COO Office) / TechOps engineering
