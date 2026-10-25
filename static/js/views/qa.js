// QA: how the answers are verified, why each layer exists, how it is implemented, and the real results (from tests/results, history included).
import { h, mount } from "../dom.js";
import { api } from "../api.js";
import { renderBlocks } from "../blocks.js";

const view = (...b) => renderBlocks(b.flat());
const pill = (r) => (r ? h("span", { class: `badge ${r.passed === r.total ? "ok" : r.passed / r.total >= 0.9 ? "warn" : "bad"}` }, `${r.passed}/${r.total} passing`) : h("span", { class: "badge" }, "not run yet"));

const layerCard = (L) => h("section", { class: "card stack" },
  h("div", { class: "fact-head" }, h("b", {}, L.title), h("span", { class: "badge info" }, L.layer), pill(L.result), L.varies ? h("span", { class: "badge warn", title: "the pass count differed between recorded runs" }, "varies between runs") : null,
    h("span", { class: "mute small" }, L.result ? `last run ${L.result.ran_at}` : "")),
  h("div", {}, h("div", { class: "note-line" }, h("b", {}, "Why it exists. "), L.why)), h("div", {}, h("div", { class: "note-line" }, h("b", {}, "How it is implemented. "), L.how)),
  h("div", {}, h("div", { class: "note-line" }, h("b", {}, "Where the expected values come from. "), L.truth)),
  L.result?.failing?.length ? h("div", { class: "callout bad" }, h("b", {}, `Failing in the last run: ${L.result.failing.join(", ")}`)) : null,
  L.history.length > 1 ? h("div", { class: "note-line" }, `History (${L.history.length} runs): ` + L.history.map((x) => `${x.passed}/${x.total}`).join(" → ")) : h("div", { class: "note-line" }, "History: one recorded run so far; every new run is appended."),
  h("div", {}, h("span", { class: "chip" }, L.command)));

export async function mountQA(root) {
  mount(root, h("div", { class: "page" }, h("div", { class: "empty" }, "Loading…")));
  const q = await api.audit("qa"), ran = q.layers.filter((l) => l.result), tot = ran.reduce((a, l) => a + l.result.total, 0), ok = ran.reduce((a, l) => a + l.result.passed, 0), j = q.judge;
  const hist = q.layers.filter((l) => l.history.length > 1);
  mount(root, h("div", { class: "page" },
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Quality assurance"), h("p", { class: "mute" }, "How we know the answers are right: five layers of checks, why each exists, how it is implemented, and the real results of the last runs (nothing here is typed in by hand; it is read from tests/results)."))),
    view({ type: "kpis", span: "full", items: [{ label: "Suites run", value: ran.length }, { label: "Checks recorded", value: tot }, { label: "Passing", value: ok, tone: ok === tot ? "ok" : "warn" }, { label: "LLM judge: rated pass (all graded scenarios)", value: j ? `${j.verdicts.pass}/${j.judged}` : "n/a", tone: "ok" }] },
      { type: "callout", span: "full", tone: "info", title: "The idea", text: "The model only routes and writes. So correctness is checked where mistakes can happen: (1) tools against ground truth with no model, (2) behaviours in multi-step dialogues, (3) safety and accounting guards, (4) the models' tool choice, (5) a stronger model judging the real answers, plus guards that run on every answer at run time." }),
    h("div", { class: "filters" }, h("a", { class: "btn", href: "#/audit/answers" }, "Real answers vs expected →"), h("a", { class: "btn", href: "#/audit/evaluations" }, "Every check, one by one →"), h("a", { class: "btn", href: "#/audit/traces" }, "Per-answer traces →")),
    q.layers.map(layerCard),
    j ? h("section", { class: "card stack" }, h("h2", {}, `The LLM judge (${j.model})`), h("div", { class: "note-line" }, "The deterministic suites above check numbers and behaviour with code. The judge adds a second opinion on the written answers: it reads each question, the expected facts and the real answer. It covers every scenario that recorded answers; anything it could not grade is listed below."), view({ type: "table", span: "full", title: "Judge coverage per suite", columns: ["suite", "scenarios", "judged", "pass", "partial", "fail"], rows: j.per_suite }),
      view({ type: "bar", span: "half", title: "Average score per criterion (1-5)", labels: Object.keys(j.avg), series: [{ name: "score", values: Object.values(j.avg) }] },
        { type: "donut", span: "half", title: "Verdicts", labels: Object.keys(j.verdicts), values: Object.values(j.verdicts) }),
      j.not_judged.length ? h("div", { class: "callout warn" }, h("b", {}, `Not judged: ${j.not_judged.join(", ")}`), h("span", {}, "The judge call itself failed (transient model error). Not counted as pass or fail.")) : null,
      j.weakest.length ? h("div", {}, h("div", { class: "note-line" }, "Answers the judge was not satisfied with, and why"), j.weakest.map((w) => h("div", { class: "note-line" }, `${w.id} (${w.verdict}): ${w.issues.join(" ")}`))) : null,
      h("details", {}, h("summary", {}, "The exact rubric the judge was given"), h("pre", { class: "code" }, q.rubric))) : null,
    h("section", { class: "card stack" }, h("h2", {}, "Guards that run on every answer"),
      h("div", { class: "note-line" }, "1. Grounding guard (code): every record ID and number in the written answer must appear in the tool result, every listed row must be mentioned, and no listed row may be called excluded. Fails → regenerate once → deterministic template."),
      h("div", { class: "note-line" }, "2. Critic sub-agent (Gemini 2.5 Pro): reads question, facts and draft and flags contradictions, invented claims, dropped rows, missing explanatory notes; one rewrite at most."),
      h("div", { class: "note-line" }, "3. Lead line and notes: a deterministic “Wells: …” line for lists, and tool notes whose IDs or figures the prose left out are appended."),
      h("div", { class: "note-line" }, `Grounding guard outcomes in the recorded traces: ${Object.entries(q.runtime_guards).map(([k, v]) => `${k}: ${v}`).join(", ") || "none recorded yet"}.`)),
    hist.length ? h("section", { class: "card" }, h("h2", {}, "Run history"), view({ type: "line", span: "full", title: "Pass rate per run (%)", labels: hist[0].history.map((x) => x.ts.slice(5)), series: hist.map((l) => ({ name: l.suite, values: l.history.map((x) => Math.round((100 * x.passed) / x.total)) })) })) : null,
    h("section", { class: "card stack" }, h("h2", {}, "Honest limits"), q.limitations.map((t) => h("div", { class: "note-line" }, "• " + t)))));
}
