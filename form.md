# Eureka 3.0 — form fields (draft v0)

Draft prepared 2026-11-07, to be finished on the Mac. Structure follows AgentGate's `form.md`. `[…]` marks a value to fill or confirm.

> **Eligibility first.** Idea submission closed on 6 November; the top-40 shortlist is out on 7 November. Ask the organisers (Elis Bechir, Sanuja George) whether agentBrain can still be entered. If not, the same text works as AgentGate's memory layer in the refinement stage (13 November): AgentGate is agentBrain's first client.

## 1. Theme
Sovereign & Responsible AI
*(alternative: Agentic AI for Mission-Critical Ops — if positioned as on-call handover and incident memory; Future of Work is excluded from the golden ticket and is a worse fit)*

## 2. Problem

**Idea title** (≤140)
agentBrain: AI Agents That Remember — Governed Shared Memory Inside the Perimeter
*(alternatives: "agentBrain: One Governed Memory for Every AI Agent, on Air-Gapped Sites" · "Stop Agents Forgetting: Sovereign Shared Memory for Teams and Their Agents")*

**One-line summary**
agentBrain gives every AI agent a team uses — GitHub Copilot, an in-house agent, a local model on an air-gapped site — one shared, governed memory: findings, decisions and handovers survive the session, every change is versioned and can be rolled back, and nothing leaves the perimeter. First client: AgentGate, where engineers already run agents on real operations; [pilot target and measured baseline].

**What problem are you solving?**
AI agents forget. What an agent finds in one session — why a job failed, which fix was rejected and why, what the person decided — is gone when the session ends. The next session, a colleague's agent or the engineer on the next shift starts from zero: the same investigation is repeated, a fix that was already denied is proposed again, and a handover is a retelling in chat. Each tool keeps its own partial memory, locked inside one vendor's assistant and invisible to the others.

On mission-critical and air-gapped sites this is worse. Cloud assistants with built-in memory cannot run there at all, and where agents do run, nothing controls what they remember: no rights on who reads what, no audit of what an agent wrote, no way to undo a bad change, and a real risk of secrets or client data ending up in a memory nobody reviews.

We see it in our own work. In AgentGate the only memory between an agent's runs is the plan it writes as a ticket comment; a new conversation, another engineer or an agent in someone's IDE cannot pick up what the last one learned. [Measured baseline: hours a week lost to repeated investigations and handovers in TechOps and Data Engineering — from a one-week time log or from tickets reopened / re-investigated.] Business owner: [name, title].

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

[Working today: … — fill after the first build. Planned: …]

What is new: memory as a governed company asset, independent of the agent. Models and assistants change every month; the memory stays, and any approved assistant plugs into it. On restricted sites it is the only way to give agents memory at all.

In line with Presight's AI use policy: agentBrain does not compete with Microsoft 365 Copilot or GitHub Copilot; it gives them — and local agents where no cloud is allowed — one governed memory that stays inside Presight's or the client's perimeter.

**Technology readiness level**
[TRL 2 today — concept, with the need shown in AgentGate's own runs. TRL 4 after the first build: memory service on the internal dev cluster, AgentGate and one IDE client connected.]

**Tags**
agentic-ai, memory, knowledge-management, sovereign-ai, on-prem, air-gapped, governance, audit, mcp, human-in-the-loop, handover

## 4. Documents
- Idea document: `eureka/agentBrain_idea.pdf` from `idea.md` [build]
- Pitch deck: [if shortlisted]

## 5. Prototype
**Type:** [Concept now → Prototype after the first build]
**Live demo URL:** [internal dev URL, on VPN — mask in screenshots]
**Repository:** [private; walkthrough on request]
**Screenshots** (masked, from the real console) [to capture]:
1. A new session continuing a ticket from an earlier session's finding — without being told.
2. The tree of a workspace with notes, documents and authors.
3. A session's change with its diff, and the one-click rollback.
4. An approval for a change to an instruction file.
5. A handover note arriving in a colleague's console.
6. Bench: two-step tasks solved with memory vs without.

**How to test it**
[Sign in → open a workspace → read the notes from the last runs on a ticket → start a new run on the same ticket and watch it pick up the earlier finding → open the change history and roll one change back.]

No client data, internal hostnames or credentials appear in any material.

## 6. Impact & team

**Expected impact**
- Fewer repeated investigations and faster handovers: [target hours a week, from the measured baseline].
- Shift and team handover: [time from handover to the receiver's first useful action — measured before / after].
- Fewer repeated mistakes: an approval denied with a reason is remembered; [share of follow-up runs that avoid a previously denied action — bench].
- Measured, not claimed: two-step bench tasks solved with memory vs without; once-failing tasks that stay fixed after a procedure change.
- Lean: no GPU for the service — about one CPU and a database; the distill step runs on the site's existing model.
- Control: every write to the memory authored and audited (100%); rollback of any session's change in one step; instruction files changed only with approval.
- Client offer: memory for agents on air-gapped and sovereign sites, where cloud assistants' memory cannot run; packaged with AgentGate or alone.
- Reuse: any team with agents — operations, data engineering, delivery, client engineering teams — by adding workspaces, not code.
- Direction of the market: AI-native companies are organised around a shared "company brain" of memory and tools ([YC talk — cite]); this is that layer, built for regulated sites.

**Submitting as:** Individual [or team of up to 5]
**Department / function:** Technical Operations (COO Office) / TechOps engineering
