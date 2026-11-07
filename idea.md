# agentBrain
### AI agents that remember — one governed, shared memory for every agent a team uses, inside the perimeter

Eureka 3.0 · Theme: Sovereign & Responsible AI · Submitted by: Rasul Karimov, Technical Operations

*Draft v0, 2026-11-07. `[…]` marks numbers to measure or confirm. External evidence and its sources: [docs/business-case-sources.md](docs/business-case-sources.md).*

---

## 1. The problem

AI agents are now part of daily engineering work, and they forget. What an agent learns in one session — the cause of a failed job, the fix a person rejected and why, the option that was chosen — is lost when the session ends. The next session, a colleague's agent, or the engineer on the next shift starts again from zero:

- **Investigations are repeated.** The same failure is diagnosed twice by two people, or twice by the same person in two conversations.
- **Rejected actions come back.** An approver denies a change with a reason; the next run proposes it again, because nothing carried the reason forward.
- **Handover is a retelling.** Passing work to a colleague means writing a summary in chat, and their agent still knows nothing.
- **Memory is locked in a tool.** Each assistant keeps its own memory — in one vendor's product, for one person. Change the assistant or the model and it is gone.

On mission-critical and air-gapped sites three more things stop teams from giving agents memory at all:

| What a regulated site requires of memory | What assistants' built-in memory gives |
|---|---|
| Stays inside the perimeter | Lives in the vendor's cloud |
| Rights: who may read what | Per user, or nothing |
| Every write attributed and audited | Not visible |
| A bad change can be undone | No history |
| No secrets or client data stored by accident | No control on what is stored |

We see the same at home. In AgentGate, where Presight engineers already run agents on real operations (7 engineers and 32 runs in its first two weeks), the only memory between runs is the plan the agent writes as a ticket comment. A new conversation, a second engineer or an agent in someone's IDE cannot pick up what the last one learned. [Baseline to measure: hours a week spent on repeated investigations and handovers in TechOps (10) and Data Engineering (14) — one-week time log plus re-opened / re-investigated tickets.] Business owner: [name].

## 2. The solution

agentBrain is a thin memory service that every agent and every platform reads and writes through the standard Model Context Protocol (MCP). It runs no model of its own; it stores, versions, controls and serves.

```
GitHub Copilot (IDE) ──┐
In-house agent runner ─┼── MCP, corporate sign-in ──► agentBrain ──► workspaces · changesets · audit
Other approved agents ─┘                                 ▲
                                                         │ facts (approvals, merge requests, finished runs)
                                          AgentGate and other platforms
```

| Part | What it does |
|---|---|
| Workspaces | Per team, system, project or person, with rights from the corporate sign-in. Hold living documents (project state, known issues, runbook drafts) and short notes: finding, decision, handover, runbook gap, event |
| Changesets | Every session is one versioned change across the whole memory — reviewed and rolled back as one |
| Instructions in the memory | Core rules and each workspace's rules, served to any agent on connect; changed only with a person's approval |
| Tools | Start a session, see the tree, read (whole or by section), search, write, hand over; platforms write events |
| Distill | On a schedule, notes become up-to-date documents; repeated gaps become proposed procedure changes |
| Console | Tree by workspace, changes with diffs and rollback, authors, handovers waiting, notes nobody reads |
| Bench | Two-step tasks with and without memory; once-failing tasks re-run after every change |

### The platform records facts, the model records conclusions

The most reliable records are not written by the model:

- **Platforms, deterministically:** an approval decided (what was proposed, who decided, the reason), an external change created (merge request, ticket comment, secret path), a run finished (status, systems touched) — taken from the audit log, not from the model's memory.
- **The agent, at set moments** named in its procedures: a conclusion reached → finding; the person chose an option → decision with the reason; the procedure did not cover the case → runbook gap.
- **A person, explicitly:** "remember that…", and handovers — an agent never hands over on its own.

### Governed by design

- **Rights:** corporate sign-in (Keycloak with Microsoft Entra ID); workspaces by group; external assistants get exactly the user's rights; the user's token is never forwarded to anything else.
- **Every write attributed:** user, session, client, links; audited like any tool call.
- **Undo:** one session's change — thirty documents or one — rolled back in one step; history kept.
- **Instruction files protected:** shared rules change only with an approval, so they do not fill up with noise.
- **No secrets stored:** a write with a secret-looking value is refused, not stored masked.
- **Notes are data, not commands:** marked as such for the agent; writes to shared workspaces carry their author.
- **Air-gapped:** no model and no external calls in the service; on a client site everything stays on site.

### Progressive disclosure: cost does not grow with the memory

An agent starts with a short entry point — the rules and a tree of paths with one-line summaries — and reads only what the task needs, a document section at a time. The prompt stays the same size whether the memory holds a hundred notes or a hundred thousand. [Measure: tokens per task with memory vs without.]

## 3. Why now, and why it is different

**The market is moving to a shared "company brain".** Investors who see the most AI-native companies describe them as organised around a central layer of shared memory and tools rather than hierarchy, with people as directly responsible owners — and report such companies reaching scale with far fewer people ([YC talk "Building And Structuring An AI Native Company" — cite the primary source]). Practitioners show the same pattern evolving independently in small product companies.

**Memory outlives the agent.** Models and assistants improve every month; large engineering organisations already switch between them for cost — one moved its engineers to an open model on its own GPUs and reports ~90% lower cost ([cite primary source]). Across a year of public agent competitions the part that did not change was the memory-and-tools layer and how agents use it. So the durable investment is the memory, built so any assistant can plug in.

**Shared memory makes mixed agents work as a team.** In public experiments, 20 people with no AI-engineering background connected their own assistants to one shared memory and raised an agent benchmark from 7 to 55 in two hours; an open swarm of about 30 different assistants on one memory reached the top-10 of a leaderboard on an open model; a handover between two people's agents dropped from 7 manual steps to 4. [Sources in docs/business-case-sources.md — confirm before quoting.]

What agentBrain adds for Presight's sites:

- **Built for sites that cannot call out.** No model inside; distill on the site's own model; nothing leaves.
- **Governance in the platform.** Rights, audit, rollback and protected instructions are enforced by the service, not asked of the model.
- **Facts from platforms, not from the model.** Approvals and outcomes are recorded deterministically, so the memory of who decided what is exact.
- **Any approved assistant.** Copilot today, another tomorrow, a local model on a client site — same memory, same rules.
- **Measured.** Two-step bench tasks with and without memory; a fixed failure must stay fixed.
- **Complements Presight's approved AI platforms** under the AI use policy: it gives Copilot and local agents a governed memory that stays inside the perimeter.

## 4. Impact

| Area | Measure | Target |
|---|---|---|
| Time | Engineer-hours on repeated investigations and handover summaries | [−X h/week from baseline] |
| Handover | Time from handover to the receiver's first useful action | [before / after] |
| Quality | Follow-up runs that repeat a previously denied action | [→ near 0, bench] |
| Effectiveness | Two-step bench tasks solved with memory vs without | [X of N vs Y of N, unsafe 0] |
| Learning | Once-failing tasks that pass after a procedure change, and stay passing | [all re-run on every change] |
| Control | Writes to memory attributed and audited; instruction changes approved | 100% |
| Lean | Infrastructure | no GPU; about one CPU and a database |
| Client offer | Sites with governed agent memory | [with AgentGate's pilot: from December 2026, subject to site approval] |
| Reuse | Teams and use cases | operations, then data engineering, delivery and client engineering teams — new workspaces, not new code |

## 5. Readiness and plan

**Today — [TRL 2]:** concept, design (`docs/plan.md`) and the need shown in AgentGate's own runs. [Update after the first build.]

| Week | Scope | Done when |
|---|---|---|
| 1 | Workspaces and changesets; start / tree / read / write / search; core and workspace rules served on start; corporate sign-in | a note written from one assistant is found by a new session in another, which follows the workspace rules |
| 2 | Events from AgentGate (approvals, merge requests, finished runs); console with history and rollback; approvals for instruction files | a new conversation on a ticket continues where the last stopped; a bad session is rolled back in one step |
| 3 | Handover with a notice; team workspaces; distill; documents by section | an on-call engineer hands over an investigation in one step |
| 4 | Bench with and without memory; demo video | measured difference, unsafe 0 |
| Then | Pilot with AgentGate on a client site; server-side sandbox for bulk edits; GitHub Copilot connected | [dates] |

## 6. Risks

| Risk | Mitigation |
|---|---|
| A log nobody reads | Distill into documents; stale notes hidden; read counts in the console |
| Wrong notes steer later work | Author and session on everything; supersede and retract; whole-session rollback; the bench measures with and without memory |
| Leaks between teams or clients | Workspace rights checked on every read; client sites keep their memory on site |
| Secrets or client data in memory | Writes with secret-looking values refused; no client data in core workspaces; [data policy per site] |
| Shared rules fill with noise | Instruction files change only with approval |
| Prompt injection through notes | Notes marked as data; authors on shared writes |
| Storage grows faster than expected | Content-addressed storage, retention for unread notes, size alarms |
| Seen as an AgentGate feature | Separate service and API; AgentGate is its first client, Copilot the second |
| Adoption | Works inside the assistants engineers already use; no new screen needed to benefit |
