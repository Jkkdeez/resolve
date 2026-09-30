"use client";

import { FormEvent, useEffect, useState } from "react";

type Candidate = { claim: string; decision: "accepted" | "rejected" | "downranked"; reasons: string[]; source: { id: string; title: string; type: string; owner: string | null; country: string | null } };
type Resolution = { decision: string; rationale: string; created_on: string; expert: { name: string; team: string } };
type Result = { outcome: "resolved" | "escalate"; answer?: string; message?: string; dimensions?: Record<string, string>; candidates: Candidate[]; expert?: { id: string; name: string; team: string }; resolution?: Resolution; open_conflict_ids?: string[] };
type Overview = { counts: { sources: number; claims: number; open_conflicts: number; human_resolutions: number }; stages: { name: string; detail: string; state: "complete" | "attention" }[]; recent_questions: { id: string; question: string; outcome: string; country: string }[] };

const scenarios = {
  trust: { label: "A / Trust the answer", question: "Can a Belgian employee work remotely from Spain for eight working days?", context: "Belgian employee · Spain · 8 working days · 30 Sep 2026" },
  conflict: { label: "B + C / Escalate & learn", question: "How should overtime be calculated for this Belgian customer?", context: "Belgian customer · overtime premium · 30 Sep 2026" },
} as const;
type Scenario = keyof typeof scenarios;

function actorHeaders(scenario: Scenario) {
  return scenario === "trust"
    ? { "x-resolve-user": "demo-consultant", "x-resolve-roles": "hr,internal" }
    : { "x-resolve-user": "payroll-consultant", "x-resolve-roles": "payroll" };
}

function Badge({ decision }: { decision: Candidate["decision"] }) {
  return <span className={`badge ${decision}`}>{decision === "accepted" ? "Used" : decision === "rejected" ? "Rejected" : "Downranked"}</span>;
}

export default function Home() {
  const [scenario, setScenario] = useState<Scenario>("trust");
  const [question, setQuestion] = useState<string>(scenarios.trust.question);
  const [result, setResult] = useState<Result | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [showExpert, setShowExpert] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const config = scenarios[scenario];
  const payload = scenario === "trust"
    ? { question, employee_country: "BE", destination_country: "ES", working_days: 8, as_of: "2026-09-30" }
    : { question, employee_country: "BE", working_days: null, as_of: "2026-09-30" };

  async function refreshOverview(activeScenario = scenario) {
    const response = await fetch("/api/v1/knowledge/overview", { headers: actorHeaders(activeScenario) });
    if (response.ok) setOverview(await response.json());
  }

  useEffect(() => { void refreshOverview("trust"); }, []);

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    setLoading(true); setError(null); setShowExpert(false);
    try {
      const response = await fetch("/api/v1/questions/answer", { method: "POST", headers: { "content-type": "application/json", ...actorHeaders(scenario) }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error("Resolve could not analyse the question.");
      setResult(await response.json());
      await refreshOverview();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong."); }
    finally { setLoading(false); }
  }

  function choose(next: Scenario) {
    setScenario(next); setQuestion(scenarios[next].question); setResult(null); setError(null); setShowExpert(false);
    void refreshOverview(next);
  }

  async function saveResolution() {
    if (!result?.open_conflict_ids?.[0]) return;
    setResolving(true); setError(null);
    try {
      const saved = await fetch(`/api/v1/conflicts/${result.open_conflict_ids[0]}/resolve`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-resolve-user": "exp-anna", "x-resolve-roles": "payroll,expert" },
        body: JSON.stringify({ decision: "Apply the 200% premium for this customer configuration; its signed customer agreement controls.", rationale: "The customer agreement was verified against the configuration. The generic 150% procedure does not govern this customer-specific case." }),
      });
      if (!saved.ok) throw new Error("The expert resolution could not be saved.");
      const answer = await fetch("/api/v1/questions/answer", { method: "POST", headers: { "content-type": "application/json", ...actorHeaders(scenario) }, body: JSON.stringify(payload) });
      if (!answer.ok) throw new Error("The verified knowledge could not be retrieved.");
      setResult(await answer.json()); setShowExpert(false);
      await refreshOverview();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong."); }
    finally { setResolving(false); }
  }

  return <main>
    <nav>
      <div className="brand"><span className="mark">R</span><span>resolve</span></div>
      <span className="nav-label">Decision intelligence / SD Worx</span>
      <span className="live-dot">LIVE PIPELINE</span>
      <span className="user">Permission-scoped demo</span>
    </nav>

    <section className="hero">
      <div><p className="eyebrow">THE KNOWLEDGE CONFIDENCE LAYER</p><h1>When the answer<br />matters, <em>show the receipts.</em></h1><p className="lede">Resolve turns conflicting organisational knowledge into accountable decisions—with a visible chain of evidence, not a black-box score.</p></div>
      <div className="hero-signal"><span className="signal-orb" /><p>LIVE DATA PIPELINE</p><strong>{overview ? `${overview.counts.sources} sources → ${overview.counts.claims} claims` : "Loading knowledge graph…"}</strong><small>Every claim is evaluated against scope, authority, jurisdiction, freshness and ownership.</small></div>
    </section>

    <section className="workspace">
      <div className="main-column">
        <div className="demo-path"><span>DEMO PATH</span><strong>Ask</strong><i>→</i><strong>Inspect</strong><i>→</i><strong>Assign ownership</strong></div>
        <div className="scenario-picker" aria-label="Demo scenarios">{(Object.keys(scenarios) as Scenario[]).map((key) => <button key={key} className={scenario === key ? "selected" : ""} onClick={() => choose(key)}>{scenarios[key].label}</button>)}</div>
        <form onSubmit={ask} className="ask">
          <div className="ask-title"><span>01</span><label htmlFor="question">Decision console</label><small>Context locked</small></div>
          <div className="ask-row"><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} /><button disabled={loading}>{loading ? "Tracing evidence…" : "Interrogate knowledge"}</button></div>
          <p>Active context: {config.context}</p>
        </form>
        {error && <p className="error">{error} Start the API at port 8000 and try again.</p>}
        {result && <ResultView result={result} onEscalate={() => setShowExpert(true)} />}
        {showExpert && <section className="expert-panel"><p className="eyebrow">EXPERT WORKSPACE · ANNA DE SMET</p><h3>Resolve the policy collision</h3><p>Anna confirms that the signed customer agreement controls this configuration. This decision will be saved as reusable organisational knowledge with an accountable owner.</p><button onClick={saveResolution} disabled={resolving}>{resolving ? "Publishing expert decision…" : "Confirm 200% premium decision"}</button></section>}
        {!result && <div className="empty"><span>↳</span><p>Run A to demonstrate contextual trust. Then run B + C to show that Resolve refuses uncertainty, brings in the right expert and learns from the resolution.</p></div>}
      </div>
      <PipelinePanel overview={overview} />
    </section>
  </main>;
}

function PipelinePanel({ overview }: { overview: Overview | null }) {
  return <aside className="pipeline">
    <p className="eyebrow">DATA PIPELINE / NOW</p>
    <h2>Knowledge has a lifecycle.</h2>
    {overview ? <><div className="counts"><div><strong>{overview.counts.sources}</strong><span>sources</span></div><div><strong>{overview.counts.claims}</strong><span>claims</span></div><div className={overview.counts.open_conflicts ? "alert-count" : ""}><strong>{overview.counts.open_conflicts}</strong><span>open conflicts</span></div></div><ol>{overview.stages.map((stage) => <li key={stage.name} className={stage.state}><i /> <div><strong>{stage.name}</strong><span>{stage.detail}</span></div></li>)}</ol>{overview.recent_questions.length > 0 && <div className="recent"><p>RECENT DECISIONS</p>{overview.recent_questions.map((item) => <div key={item.id}><span className={item.outcome}>{item.outcome === "resolved" ? "ANSWERED" : "ESCALATED"}</span><small>{item.question}</small></div>)}</div>}</> : <p className="loading-copy">Loading the permissioned source view…</p>}
    <div className="pipeline-note"><span>✦</span><p>Gemini / Vertex will extract and retrieve. Resolve keeps authority and access decisions deterministic.</p></div>
  </aside>;
}

function ResultView({ result, onEscalate }: { result: Result; onEscalate: () => void }) {
  const receiptOwner = result.resolution?.expert.name || result.expert?.name || result.dimensions?.ownership || "No accountable owner";
  const guardrail = result.outcome === "escalate" ? "Resolve declined to choose between live conflicts." : result.resolution ? "A designated expert accepted accountability." : "Scope, jurisdiction, freshness and ownership were checked.";
  return <section className="results">
    <div className={`answer ${result.outcome}`}>
      <p className="eyebrow">{result.resolution ? "HUMAN-VERIFIED KNOWLEDGE" : result.outcome === "resolved" ? "DECISION READY" : "SAFE ESCALATION"}</p>
      <h2>{result.answer || result.message}</h2>
      {result.resolution && <p className="resolution-copy"><strong>{result.resolution.expert.name}</strong> · {result.resolution.expert.team} · resolved {result.resolution.created_on}. {result.resolution.rationale}</p>}
      {result.outcome === "escalate" && result.expert && <><div className="expert">Assigned expert <strong>{result.expert.name}</strong> · {result.expert.team}</div><button className="expert-action" onClick={onEscalate}>Open Anna’s expert workspace <span>→</span></button></>}
    </div>
    <section className={`receipt ${result.outcome}`}>
      <div className="receipt-title"><span className="receipt-mark">R</span><div><p>RESOLVE RECEIPT</p><strong>A decision people can own.</strong></div><small>{result.outcome === "resolved" ? "READY" : "HOLD"}</small></div>
      <div className="receipt-grid"><div><span>Decision state</span><strong>{result.outcome === "resolved" ? "Safe to act" : "Awaiting expert"}</strong></div><div><span>Accountability</span><strong>{receiptOwner}</strong></div><div><span>Guardrail applied</span><strong>{guardrail}</strong></div></div>
    </section>
    {result.dimensions && <div className="dimensions"><div className="section-title"><p className="eyebrow">EXPLAINABLE DECISION</p><h3>Why Resolve can stand behind this</h3></div><div className="dimension-grid">{Object.entries(result.dimensions).map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div></div>}
    <div className="evidence"><div><p className="eyebrow">EVIDENCE LEDGER</p><h3>{result.candidates.length} claims surfaced. Every one accounted for.</h3></div>{result.candidates.map((candidate) => <article key={candidate.source.id} className={candidate.decision}><div className="source-head"><div><Badge decision={candidate.decision} /><h4>{candidate.source.title}</h4><p>{candidate.source.type.replaceAll("_", " ")} · {candidate.source.country || "No jurisdiction"} · {candidate.source.owner || "No owner"}</p></div><span className="source-id">{candidate.source.id.slice(-6)}</span></div><blockquote>{candidate.claim}</blockquote><ul>{candidate.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></article>)}</div>
    <footer>{result.resolution ? "Scenario C complete — the expert decision is now a governed knowledge asset." : result.outcome === "escalate" ? "Scenario B — Resolve will not make an arbitrary choice between authoritative conflicts." : "Scenario A — stale, wrong-jurisdiction and ownerless evidence never enters the decision."}</footer>
  </section>;
}
