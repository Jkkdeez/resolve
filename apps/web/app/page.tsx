"use client";

import { FormEvent, useState } from "react";

type Candidate = { claim: string; decision: "accepted" | "rejected" | "downranked"; reasons: string[]; source: { id: string; title: string; type: string; owner: string | null; country: string | null } };
type Resolution = { decision: string; rationale: string; created_on: string; expert: { name: string; team: string } };
type Result = { outcome: "resolved" | "escalate"; answer?: string; message?: string; dimensions?: Record<string, string>; candidates: Candidate[]; expert?: { id: string; name: string; team: string }; resolution?: Resolution; open_conflict_ids?: string[] };

const scenarios = {
  trust: { label: "Scenario A · Resolve", question: "Can a Belgian employee work remotely from Spain for eight working days?", context: "Belgian employee · Spain · 8 working days · 30 Sep 2026" },
  conflict: { label: "Scenario B/C · Escalate & learn", question: "How should overtime be calculated for this Belgian customer?", context: "Belgian customer · overtime premium · 30 Sep 2026" },
} as const;
type Scenario = keyof typeof scenarios;

function Badge({ decision }: { decision: Candidate["decision"] }) { return <span className={`badge ${decision}`}>{decision === "accepted" ? "Used" : decision === "rejected" ? "Rejected" : "Downranked"}</span>; }

export default function Home() {
  const [scenario, setScenario] = useState<Scenario>("trust");
  const [question, setQuestion] = useState<string>(scenarios.trust.question);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [showExpert, setShowExpert] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const config = scenarios[scenario];
  const payload = scenario === "trust" ? { question, employee_country: "BE", destination_country: "ES", working_days: 8, as_of: "2026-09-30" } : { question, employee_country: "BE", working_days: null, as_of: "2026-09-30" };
  const headers = scenario === "trust" ? { "x-resolve-user": "demo-consultant", "x-resolve-roles": "hr,internal" } : { "x-resolve-user": "payroll-consultant", "x-resolve-roles": "payroll" };

  async function ask(event?: FormEvent) {
    event?.preventDefault(); setLoading(true); setError(null); setShowExpert(false);
    try {
      const response = await fetch("/api/v1/questions/answer", { method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error("Resolve could not analyse the question.");
      setResult(await response.json());
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong."); }
    finally { setLoading(false); }
  }

  function choose(next: Scenario) { setScenario(next); setQuestion(scenarios[next].question); setResult(null); setError(null); setShowExpert(false); }

  async function saveResolution() {
    if (!result?.open_conflict_ids?.[0]) return;
    setResolving(true); setError(null);
    try {
      const save = await fetch(`/api/v1/conflicts/${result.open_conflict_ids[0]}/resolve`, { method: "POST", headers: { "content-type": "application/json", "x-resolve-user": "exp-anna", "x-resolve-roles": "payroll,expert" }, body: JSON.stringify({ decision: "Apply the 200% premium for this customer configuration; its signed customer agreement controls.", rationale: "The customer agreement was verified against the configuration. The generic 150% procedure does not govern this customer-specific case." }) });
      if (!save.ok) throw new Error("The expert resolution could not be saved.");
      const answer = await fetch("/api/v1/questions/answer", { method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify(payload) });
      if (!answer.ok) throw new Error("The verified knowledge could not be retrieved.");
      setResult(await answer.json()); setShowExpert(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong."); }
    finally { setResolving(false); }
  }

  return <main>
    <nav><div className="brand"><span className="mark">R</span>Resolve</div><span className="nav-label">Knowledge trust layer</span><span className="user">Secure, permission-scoped demo</span></nav>
    <section className="hero"><p className="eyebrow">SD WORX · TECTONIC HACKATHON</p><h1>Find the answer.<br /><em>Know why it is safe.</em></h1><p className="lede">Resolve ranks knowledge by authority, context, ownership and freshness—and sends unresolved conflicts to accountable experts.</p></section>
    <section className="workspace">
      <div className="scenario-picker">{(Object.keys(scenarios) as Scenario[]).map((key) => <button key={key} className={scenario === key ? "selected" : ""} onClick={() => choose(key)}>{scenarios[key].label}</button>)}</div>
      <form onSubmit={ask} className="ask"><label htmlFor="question">Ask Resolve</label><div className="ask-row"><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} /><button disabled={loading}>{loading ? "Resolving…" : "Resolve question"}</button></div><p>Context: {config.context}</p></form>
      {error && <p className="error">{error} Start the API at port 8000 and try again.</p>}
      {result && <ResultView result={result} onEscalate={() => setShowExpert(true)} />}
      {showExpert && <section className="expert-panel"><p className="eyebrow">EXPERT WORKSPACE · ANNA DE SMET</p><h3>Resolve the policy conflict</h3><p>Anna confirms the signed customer agreement controls this configuration. Saving it makes a reusable, human-verified knowledge item.</p><button onClick={saveResolution} disabled={resolving}>{resolving ? "Saving resolution…" : "Confirm 200% premium decision"}</button></section>}
      {!result && <div className="empty"><span>01</span><p>Start with the trusted remote-work answer, then demonstrate the conflict-to-expert loop.</p></div>}
    </section>
  </main>;
}

function ResultView({ result, onEscalate }: { result: Result; onEscalate: () => void }) {
  return <section className="results">
    <div className={`answer ${result.outcome}`}><p className="eyebrow">{result.resolution ? "HUMAN-VERIFIED KNOWLEDGE" : result.outcome === "resolved" ? "RESOLVED · HIGH CONFIDENCE" : "SAFE ESCALATION"}</p><h2>{result.answer || result.message}</h2>{result.resolution && <p><strong>{result.resolution.expert.name}</strong> · {result.resolution.expert.team} · resolved {result.resolution.created_on}. {result.resolution.rationale}</p>}{result.outcome === "escalate" && result.expert && <><div className="expert">Recommended expert <strong>{result.expert.name}</strong> · {result.expert.team}</div><button className="expert-action" onClick={onEscalate}>Open Anna’s expert workspace</button></>}</div>
    {result.dimensions && <div className="dimensions"><h3>Why this answer is trustworthy</h3><div className="dimension-grid">{Object.entries(result.dimensions).map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div></div>}
    <div className="evidence"><div><p className="eyebrow">EVIDENCE REVIEW</p><h3>{result.candidates.length} relevant claims, evaluated in context</h3></div>{result.candidates.map((candidate) => <article key={candidate.source.id} className={candidate.decision}><div><Badge decision={candidate.decision} /><h4>{candidate.source.title}</h4><p>{candidate.source.type.replaceAll("_", " ")} · {candidate.source.country || "No jurisdiction"} · {candidate.source.owner || "No owner"}</p></div><blockquote>{candidate.claim}</blockquote><ul>{candidate.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></article>)}</div>
    <footer>{result.resolution ? "Scenario C complete: the expert’s decision now answers the same question safely." : result.outcome === "escalate" ? "Scenario B: Resolve refuses to choose between current, authoritative conflicts." : "Scenario A: historical, wrong-jurisdiction, and ownerless evidence were excluded."}</footer>
  </section>;
}
