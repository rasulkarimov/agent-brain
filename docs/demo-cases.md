# agentBrain — demo cases

Cases for the presentation, each from the running prototype (dev cluster, 7 Nov 2026). "Live-tested" means it ran against the deployed service; the rest are to verify before the demo. Names of colleagues and internal hosts are masked on slides.

## 1. The next session starts where the last one stopped (the headline)

**The pain, from real usage.** From 4 to 6 Nov one engineer worked on the Airflow DAG `spark_landing_to_bronze_streaming` in a single AgentGate conversation of 19 messages — "running as expected?", "why did the first try fail?", "why has this failed?". Everything found there (driver OOM, the fix, the executor-failure cycle) lived only in that conversation: no colleague, new conversation or other assistant could see it.

**With agentBrain (live-tested, run `run-20261107-180411-bded1d`).** The findings of those conversations were in the memory as two notes. A new conversation was asked, without any hint about memory: *"spark_landing_to_bronze_streaming failed again tonight with Max number of executor failures. What's going on and what should I try?"*

What the local model (Qwen3.8 27B, on-prem) did on its own:
1. `brain_start` first, then read both notes (driver OOM fixed by 2g; executor-failure cycle, open question: why do executors die).
2. Took the open question from the note as its starting point: found `termination reason: OOMKilled` at every lost executor in the driver logs, checked executor memory in the YAML and the batch size in the job.
3. Answered with the cause and two fixes (executor memory, smaller micro-batches), and said the earlier driver OOM is already fixed — it did not re-investigate it.
4. Wrote a new `finding` back, linked to the DAG, the branch and its run: the next conversation starts from this one.

Facts for the slide: 24 tool calls, 3 of them to the memory; ~5 minutes; the answer goes one layer deeper than the earlier conversation. We do not claim a time saving from one run — the bench (with vs without memory) is the measure.

**Demo:** open the run in AgentGate (first tool call `brain_start`), then the new note in the agentBrain console with its author, session and link to the run.

## 2. One memory for every assistant

An engineer's own Claude Code on a laptop and AgentGate's on-prem agent read and write the same memory.

**Demo (live, by the presenter):** in Claude Code connected to agentBrain (Keycloak sign-in in the browser, no token copied anywhere): *"Start a session about spark_landing_to_bronze_streaming and tell me what the team already knows."* It returns the three notes above, including the one AgentGate's agent wrote. Then ask it to record a decision ("we try smaller batches first, 6g only if that fails"); the next AgentGate run sees the decision.

The audit page shows the same memory used by two clients: `agentbrain-mcp/claude-code` and `agentgate`.

## 2b. Claude and Codex continue each other's work (live-tested)

**The pain, from our own sessions.** Twice in October work started in Claude Desktop was continued in Codex — the Airflow move to the new Keycloak, and the AgentGate bench — and both times Codex was told to read Claude's session log by hand to pick up the context.

**With agentBrain.** Codex CLI, signed in through the same Keycloak, recorded both outcomes as notes (Airflow on the new Keycloak with MR !193 done and MR !194 pending; AgentGate MLflow spans MR !1 with tests not yet run). Then Claude Code was asked only *"I'm picking up the Keycloak migration of Airflow — what's done, what's pending, who recorded it?"* It answered from one `brain_start`: done on dataplatform (recorded by Codex), the dev 403 fix (recorded by Claude Code), and what is still pending — MR !194 deploys on merge, the realm idle timeout to confirm, the Airflow core upgrade.

Three assistants now share the memory: AgentGate's on-prem agent, Claude Code and Codex — the audit shows each by name.

## 3. Handover in one step (live-tested)

*"Hand this over to <colleague>: executor OOM found, MR not opened yet, waiting on 6g vs smaller batches."* → a `handover` note in the colleague's own workspace. Their next session, in any assistant, starts with it (`handovers_for_you`), once.

## 4. The platform writes facts, not the model (live-tested)

Every approval decided in AgentGate is recorded by the gateway as an `event` note: who approved or denied, the reason, the merge request link. A denial with a reason is then visible to the next run, which does not repeat the mistake.

Run `run-20261107-181253-ac6434` proposed a one-line README change; it was denied with the reason "README changes go through the docs MR, not from an agent run". Seconds later the memory held `gitlab_propose_change denied by …: Demo line in README` with the reason and the arguments, written by the gateway, not by the model. The agent reported the denial, stopped, and offered to record the rule.

## 5. Guardrails (live-tested)

All refused at the door, each with a message that tells the agent what to do instead:

| Attempt | Answer |
|---|---|
| a note with `MINIO_SECRET_KEY: …` | refused: secret-looking value; say where the secret lives (its Vault path) |
| an agent rewriting `AGENTS.md` | refused: instruction files change only with a person's approval |
| editing someone's note | refused: notes are not edited, write a new note that links it |
| writing into a colleague's own workspace | refused (only a handover may) |
| writing a document changed since it was read | conflict: read the new version, merge, write again |

## 6. One click undoes a bad session (live-tested)

Every session is one changeset. In the console, Sessions → Roll back: everything that session wrote across the memory goes back to how it was, and the rollback is itself a recorded session.

## 7. Rules live in the memory (to verify live)

An admin edits `team/dataplatform/AGENTS.md` in the console (e.g. "link the Airflow DAG and the branch on every note"); the next session of every assistant gets the rule from `brain_start`. Same rules for Copilot, Claude Code and the on-prem agent, without touching any of them.

## Running order (5 minutes)

1. The pain: three days, 19 messages on one DAG, all of it locked in one conversation (30 s, a slide).
2. Case 1 in AgentGate and the console (90 s).
3. Case 2 live in Claude Code (60 s).
4. Guardrails and rollback in the console (60 s).
5. Handover and rules (30 s), then what is next: distill, the bench with and without memory, Copilot.
