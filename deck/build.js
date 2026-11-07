const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/rasul.karimov/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/64b33d11-bd19-44b3-9946-87048a845887/d3dd1a5c-eaac-4a5e-baa9-056b0147c0c8/skills/pptx/scripts/apply_theme.js");

const SHOTS = "/Users/rasul.karimov/projects/git/agent-gate/eureka/agentbrain";
const OUT = process.argv[2] || "agentBrain_deck.pptx";

// The console's own palette: ink background, violet for the memory, kind colours for notes.
const THEME = {
  name: "agentBrain",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "15171C", lt1: "E2E6EE", dk2: "222631", lt2: "8E97A6",
    accent1: "A493F7", accent2: "4CBF8C", accent3: "F0A35E", accent4: "EF7D8A", accent5: "78A6F0", accent6: "5C6573",
    hlink: "A493F7", folHlink: "B39BF8",
  },
};
const HEX = { panel: "1B1E25", raised: "222631", rule: "2B303C", ink: "E2E6EE", muted: "8E97A6", faint: "5C6573",
  violet: "A493F7", green: "4CBF8C", orange: "F0A35E", red: "EF7D8A", blue: "78A6F0", bg: "15171C" };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.title = "agentBrain — Eureka 3.0";
pres.author = "Rasul Karimov";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.bg },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 22, bold: true,
      color: C.background1, align: "left", valign: "top", margin: 0 }, text: "" } },
    { text: { text: "agentBrain · Eureka 3.0", options: { x: 0.5, y: 5.2, w: 4, h: 0.25, fontSize: 9, color: C.background2, margin: 0 } } },
  ],
  slideNumber: { x: 9.1, y: 5.2, w: 0.4, h: 0.25, fontSize: 9, color: HEX.muted, align: "right" },
});
pres.defineSlideMaster({ title: "DARK", background: { color: HEX.bg } });

const T = (slide, text, opts) => slide.addText(text, { isTextBox: true, margin: 0, fontFace: "Calibri", color: HEX.ink, ...opts });
const card = (slide, x, y, w, h, name, fill = HEX.panel) =>
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: HEX.rule, width: 0.75 }, objectName: name });
const dot = (slide, x, y, color, d = 0.16) => slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 } });
const shot = (slide, file, x, y, w, name) => {
  const h = w * 1720 / 2880;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.04, y: y - 0.04, w: w + 0.08, h: h + 0.08, rectRadius: 0.06, fill: { color: HEX.rule }, line: { color: HEX.rule } });
  slide.addImage({ path: `${SHOTS}/${file}`, x, y, w, h, altText: name, objectName: name });
  return h;
};

// 1 — title
{
  const s = pres.addSlide({ masterName: "DARK" });
  T(s, "agentBrain", { x: 0.5, y: 0.7, w: 4.6, h: 0.8, fontSize: 40, bold: true, fontFace: "Arial" });
  T(s, "AI agents that remember", { x: 0.5, y: 1.5, w: 4.6, h: 0.45, fontSize: 20, color: HEX.violet });
  T(s, "One governed, shared memory for every assistant a team uses — on Presight's own infrastructure.", { x: 0.5, y: 2.05, w: 4.3, h: 0.8, fontSize: 14, color: HEX.muted });
  const clients = [["AgentGate on-prem agent", HEX.green], ["Claude Code", HEX.violet], ["Codex", HEX.blue]];
  T(s, "Working today with", { x: 0.5, y: 3.15, w: 4, h: 0.3, fontSize: 11, color: HEX.muted });
  clients.forEach(([name, c], i) => { dot(s, 0.5, 3.58 + i * 0.36, c); T(s, name, { x: 0.78, y: 3.5 + i * 0.36, w: 3.5, h: 0.3, fontSize: 14 }); });
  T(s, "Sovereign & Responsible AI · Rasul Karimov, Technical Operations", { x: 0.5, y: 5.05, w: 5, h: 0.3, fontSize: 10, color: HEX.faint });
  shot(s, "ab-00-graph-all.png", 5.15, 0.85, 4.45, "The memory as a graph");
  T(s, "The live memory: notes from three assistants and what they link", { x: 5.15, y: 3.65, w: 4.45, h: 0.3, fontSize: 11, color: HEX.muted });
  s.addNotes("agentBrain is the shared memory of a team's AI agents. Three different assistants already use it on our internal cluster.");
}

// 2 — problem
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("What an agent learns stays locked in one conversation", { placeholder: "title" });
  T(s, "One engineer, one failing Airflow job: three days, 19 messages, a single AgentGate conversation", { x: 0.5, y: 1.05, w: 9, h: 0.35, fontSize: 14, color: HEX.muted });
  const asks = [["Day 1", "the DAG uses spark-delta-streaming.yaml with a specific image…"], ["Day 3 · 08:45", "changed the version in the yaml, still failing"],
                ["Day 3 · 11:17", "why did the first try fail?"], ["Day 3 · 12:53", "why has this failed?"]];
  s.addShape(pres.shapes.LINE, { x: 0.7, y: 1.95, w: 8.6, h: 0, line: { color: HEX.rule, width: 1.5 } });
  asks.forEach(([t, q], i) => {
    const x = 0.5 + i * 2.28;
    dot(s, x + 0.12, 1.87, HEX.violet);
    T(s, t, { x, y: 1.55, w: 2.1, h: 0.25, fontSize: 11, color: HEX.violet, bold: true });
    card(s, x, 2.15, 2.13, 0.75, `ask-${i}`);
    T(s, `"${q}"`, { x: x + 0.12, y: 2.2, w: 1.9, h: 0.65, fontSize: 12, italic: true, valign: "middle" });
  });
  T(s, "Driver out of memory, the fix, then a new failure cycle — all found, all living only in that thread.", { x: 0.5, y: 3.05, w: 9, h: 0.3, fontSize: 13 });
  card(s, 0.5, 3.5, 9, 1.4, "handover-pain", HEX.raised);
  T(s, "No colleague, new conversation or other assistant can see it", { x: 0.75, y: 3.62, w: 8.5, h: 0.3, fontSize: 15, bold: true, color: HEX.orange });
  T(s, [
    { text: "Twice in October work started in Claude was continued in Codex — Codex had to be told to read Claude's session log by hand.", options: { bullet: true, breakLine: true } },
    { text: "Every assistant keeps its own memory, locked in one vendor's tool, invisible to the others and to colleagues.", options: { bullet: true } },
  ], { x: 0.75, y: 3.98, w: 8.5, h: 0.85, fontSize: 13, paraSpaceAfter: 3 });
}

// 3 — what regulated sites need
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Memory a regulated site can accept", { placeholder: "title" });
  T(s, "Assistants' built-in memory can't run on sites that cannot call out — and where agents do run, nothing controls what they remember", { x: 0.5, y: 1.05, w: 9, h: 0.5, fontSize: 13, color: HEX.muted });
  const rows = [
    ["Stays inside the perimeter", "Lives in the vendor's cloud", "On our cluster; no model inside, no external calls"],
    ["Rights: who may read what", "Per user, or nothing", "Workspaces by Keycloak group; agents get exactly the user's rights"],
    ["Every write attributed", "Not visible", "Author, assistant, session and links on every note; full audit"],
    ["A bad change can be undone", "No history", "Every session is one change, rolled back in one click"],
    ["No secrets stored by accident", "No control", "A write with a secret-looking value is refused"],
  ];
  const head = { bold: true, color: HEX.muted, fontSize: 11, fill: { color: HEX.panel } };
  const data = [[{ text: "Requirement", options: head }, { text: "Built-in assistant memory", options: head }, { text: "agentBrain", options: { ...head, color: HEX.violet } }]];
  rows.forEach(([a, b, c]) => data.push([
    { text: a, options: { bold: true } }, { text: b, options: { color: HEX.red } }, { text: c, options: { color: HEX.green } }]));
  s.addTable(data, { x: 0.5, y: 1.7, w: 9, colW: [2.6, 2.3, 4.1], fontFace: "Calibri", fontSize: 13, color: HEX.ink,
    border: { type: "solid", pt: 0.75, color: HEX.rule }, fill: { color: HEX.bg }, rowH: 0.52, valign: "middle", margin: 0.08 });
}

// 4 — solution
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("One thin memory service, reached through MCP", { placeholder: "title" });
  const clients = [["AgentGate on-prem agent", HEX.green], ["Claude Code", HEX.violet], ["Codex", HEX.blue], ["GitHub Copilot (next)", HEX.faint]];
  clients.forEach(([n, c], i) => {
    card(s, 0.5, 1.2 + i * 0.62, 2.4, 0.5, `client-${i}`);
    dot(s, 0.65, 1.37 + i * 0.62, c);
    T(s, n, { x: 0.92, y: 1.27 + i * 0.62, w: 1.95, h: 0.36, fontSize: 12, valign: "middle" });
  });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 3.0, y: 2.0, w: 0.9, h: 0.45, fill: { color: HEX.violet }, line: { color: HEX.violet } });
  T(s, "MCP · Keycloak sign-in, as the user", { x: 2.85, y: 2.5, w: 1.25, h: 0.5, fontSize: 9, color: HEX.muted, align: "center" });
  card(s, 4.05, 1.2, 2.6, 2.4, "brain", HEX.raised);
  T(s, "agentBrain", { x: 4.25, y: 1.32, w: 2.3, h: 0.4, fontSize: 18, bold: true, color: HEX.violet, fontFace: "Arial" });
  T(s, [
    { text: "Workspaces of notes and documents", options: { bullet: true, breakLine: true } },
    { text: "Changesets: one session = one change", options: { bullet: true, breakLine: true } },
    { text: "Rules for agents live in the memory", options: { bullet: true, breakLine: true } },
    { text: "Audit of every call", options: { bullet: true } },
  ], { x: 4.25, y: 1.78, w: 2.3, h: 1.7, fontSize: 12, paraSpaceAfter: 4 });
  s.addShape(pres.shapes.LEFT_ARROW, { x: 6.75, y: 2.0, w: 0.75, h: 0.45, fill: { color: HEX.green }, line: { color: HEX.green } });
  card(s, 7.6, 1.2, 1.9, 2.4, "platforms");
  T(s, "Platforms", { x: 7.75, y: 1.32, w: 1.6, h: 0.35, fontSize: 14, bold: true, color: HEX.green });
  T(s, "AgentGate writes facts — approvals, merge requests, runs — deterministically, not through the model", { x: 7.75, y: 1.72, w: 1.65, h: 1.7, fontSize: 11 });
  const ideas = [
    ["The platform records facts, the model records conclusions", HEX.green],
    ["No model inside: works on sites that cannot call out", HEX.violet],
    ["Any approved assistant plugs in — the memory outlives the tool", HEX.blue],
  ];
  ideas.forEach(([t, c], i) => { dot(s, 0.5, 3.98 + i * 0.36, c, 0.14); T(s, t, { x: 0.75, y: 3.9 + i * 0.36, w: 8.7, h: 0.3, fontSize: 13 }); });
}

// 5 — working today: the case
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Working today: picking up where the last session stopped", { placeholder: "title" });
  card(s, 0.5, 1.1, 9, 0.62, "prompt", HEX.raised);
  T(s, [
    { text: "Asked AgentGate, on the on-prem model, with no hint about memory:  ", options: { color: HEX.muted } },
    { text: "\"The job failed again tonight with Max number of executor failures. What's going on and what should I try?\"", options: { italic: true } },
  ], { x: 0.7, y: 1.17, w: 8.6, h: 0.5, fontSize: 12, valign: "middle" });
  const steps = [
    ["Opened the memory first", "Read the two earlier findings — driver OOM (fixed), and the open question: why do executors die?"],
    ["Started from the open question", "Found OOMKilled at every lost executor; checked memory and batch size in the config"],
    ["Did not redo old work", "Said the driver issue was already fixed instead of investigating it again"],
    ["Wrote its finding back", "Linked to the job, the branch and its run — for the next session, anyone's"],
  ];
  steps.forEach(([h, b], i) => {
    const x = 0.5 + i * 2.28;
    card(s, x, 1.95, 2.13, 2.3, `step-${i}`);
    s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: 2.08, w: 0.42, h: 0.42, fill: { color: HEX.violet }, line: { color: HEX.violet } });
    T(s, String(i + 1), { x: x + 0.15, y: 2.08, w: 0.42, h: 0.42, fontSize: 15, bold: true, color: HEX.bg, align: "center", valign: "middle" });
    T(s, h, { x: x + 0.15, y: 2.6, w: 1.85, h: 0.5, fontSize: 13, bold: true });
    T(s, b, { x: x + 0.15, y: 3.1, w: 1.85, h: 1.1, fontSize: 11, color: HEX.muted });
  });
  T(s, "Real run on the dev cluster: 24 tool calls, 3 of them to the memory, ~5 minutes. Time saved is measured on the bench, not claimed from one run.",
    { x: 0.5, y: 4.45, w: 9, h: 0.5, fontSize: 11, color: HEX.muted });
}

// 6 — three assistants, one memory
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Claude and Codex continue each other's work", { placeholder: "title" });
  shot(s, "ab-01-graph.png", 0.5, 1.1, 5.6, "A decision recorded by Codex, open beside the graph");
  T(s, "A decision recorded by Codex: Airflow moved to the new Keycloak, MR !194 still pending", { x: 0.5, y: 4.5, w: 5.6, h: 0.45, fontSize: 10, color: HEX.muted });
  card(s, 6.4, 1.1, 3.1, 3.85, "story");
  T(s, "No log reading any more", { x: 6.6, y: 1.25, w: 2.8, h: 0.35, fontSize: 15, bold: true, color: HEX.violet });
  T(s, [
    { text: "Codex recorded what it finished and what is pending.", options: { bullet: true, breakLine: true } },
    { text: "Claude Code was asked only: \"I'm picking up the Keycloak migration — what's done, what's pending, who recorded it?\"", options: { bullet: true, breakLine: true } },
    { text: "One brain_start: done (by Codex), the dev fix (by Claude Code), and the three open items.", options: { bullet: true } },
  ], { x: 6.6, y: 1.7, w: 2.75, h: 2.4, fontSize: 12, paraSpaceAfter: 5 });
  T(s, "Every note shows who wrote it and through which assistant", { x: 6.6, y: 4.2, w: 2.75, h: 0.6, fontSize: 11, color: HEX.muted, italic: true });
}

// 7 — governed by design
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Governed by the platform, not asked of the model", { placeholder: "title" });
  shot(s, "ab-04-audit.png", 4.2, 1.1, 5.3, "Audit: every call by every client");
  T(s, "Audit: every call by Claude Code, Codex and AgentGate — refusals included", { x: 4.2, y: 4.35, w: 5.3, h: 0.3, fontSize: 10, color: HEX.muted });
  const rules = [
    ["A secret in a note", "refused: say where it lives instead", HEX.red],
    ["An agent rewriting the rules", "refused: needs a person's approval", HEX.red],
    ["Editing someone's note", "refused: write a new note that links it", HEX.orange],
    ["A document changed since read", "conflict, not an overwrite", HEX.orange],
    ["A bad session", "rolled back in one click", HEX.green],
  ];
  rules.forEach(([a, b, c], i) => {
    const y = 1.1 + i * 0.68;
    card(s, 0.5, y, 3.5, 0.58, `rule-${i}`);
    dot(s, 0.65, y + 0.21, c, 0.15);
    T(s, a, { x: 0.92, y: y + 0.06, w: 3.0, h: 0.24, fontSize: 12, bold: true });
    T(s, b, { x: 0.92, y: y + 0.3, w: 3.0, h: 0.24, fontSize: 11, color: HEX.muted });
  });
}

// 8 — impact
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Impact: measured in the pilot, not claimed", { placeholder: "title" });
  const kpis = [
    ["Repeated investigations", "Follow-up conversations that start from an earlier note instead of from zero — from the audit; hours from a one-week time log before and after"],
    ["Handover", "Time from a handover to the receiver's first useful action, before and after"],
    ["Repeated mistakes", "Follow-up runs that repeat a denied action — near zero on the bench"],
    ["Control", "Writes attributed and audited, rules changed only with approval — 100%"],
  ];
  kpis.forEach(([h, b], i) => {
    const x = 0.5 + (i % 2) * 4.6, y = 1.15 + Math.floor(i / 2) * 1.45;
    card(s, x, y, 4.4, 1.3, `kpi-${i}`);
    T(s, h, { x: x + 0.2, y: y + 0.13, w: 4.0, h: 0.3, fontSize: 14, bold: true, color: HEX.violet });
    T(s, b, { x: x + 0.2, y: y + 0.48, w: 4.0, h: 0.75, fontSize: 12 });
  });
  T(s, [
    { text: "Lean: ", options: { bold: true, color: HEX.green } },
    { text: "no GPU — one small container and a database. ", options: {} },
    { text: "Reuse: ", options: { bold: true, color: HEX.green } },
    { text: "any team with agents adds a workspace, not code. Pilot: TechOps (10) and Data Engineering (14).", options: {} },
  ], { x: 0.5, y: 4.1, w: 9, h: 0.75, fontSize: 13 });
}

// 9 — readiness and the ask
{
  const s = pres.addSlide({ masterName: "DARK" });
  T(s, "TRL 5", { x: 0.5, y: 0.6, w: 3, h: 1.0, fontSize: 60, bold: true, color: HEX.violet, fontFace: "Arial" });
  T(s, "Running on the internal dev cluster with the corporate sign-in; tested end to end with three assistants on real investigations. Not yet in daily team use.",
    { x: 0.5, y: 1.65, w: 4.0, h: 1.2, fontSize: 13, color: HEX.muted });
  T(s, "Business owner: Atul Vishwakarma, Director – Technical Operations", { x: 0.5, y: 3.0, w: 4.0, h: 0.6, fontSize: 12 });
  T(s, "Demo: agentbrain.intdev.presight.ai (VPN)", { x: 0.5, y: 3.6, w: 4.0, h: 0.3, fontSize: 12, color: HEX.violet });
  const next = [
    ["Pilot", "TechOps and Data Engineering; baseline week, then with memory"],
    ["Distill", "Notes become up-to-date documents; repeated gaps become procedure changes"],
    ["Bench", "Tasks with and without memory; a fixed failure must stay fixed"],
    ["More assistants", "GitHub Copilot connected the same way; team workspaces from groups"],
  ];
  T(s, "Next", { x: 5.2, y: 0.65, w: 4, h: 0.4, fontSize: 18, bold: true });
  next.forEach(([h, b], i) => {
    const y = 1.15 + i * 0.85;
    card(s, 5.2, y, 4.3, 0.72, `next-${i}`);
    T(s, h, { x: 5.4, y: y + 0.08, w: 3.9, h: 0.26, fontSize: 13, bold: true, color: HEX.green });
    T(s, b, { x: 5.4, y: y + 0.36, w: 3.9, h: 0.3, fontSize: 11, color: HEX.muted });
  });
  T(s, "The memory outlives the assistant.", { x: 0.5, y: 4.7, w: 9, h: 0.4, fontSize: 16, italic: true, color: HEX.ink });
}

pres.writeFile({ fileName: OUT }).then(() => applyTheme(OUT, THEME)).then(() => console.log("written", OUT));
