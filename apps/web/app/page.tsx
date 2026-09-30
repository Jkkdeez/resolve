"use client";

import { FormEvent, useState } from "react";

type Candidate = { claim: string; value: number | null; decision: "accepted" | "rejected" | "downranked"; reasons: string[]; source: { id: string; title: string; type: string; owner: string | null; country: string | null } };
type Result = { outcome: "resolved" | "escalate"; answer?: string; message?: string; dimensions?: Record<string, string>; candidates: Candidate[]; winner?: Candidate; expert?: { name: string; team: string }; open_conflict_ids?: string[] };

const initialQuestion = "Can a Belgian employee work remotely from Spain for eight working days?";

function DecisionBadge({ decision }: { decision: Candidate["decision"] }) {
  return <span className={`badge ${decision}`}>{decision === "accepted" ? "Used" : decision === "rejected" ? "Rejected" : "Downranked"}</span>;
}

export default function Home() {
  const [question, setQuestion] = useState(initialQuestion);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(null);
    try {
      const response = await fetch("/api/v1/questions/answer", {
        method: "POST",
        headers: { "content-type": "application/json", "x-resolve-user": "demo-consultant", "x-resolve-roles": "hr,internal" },
        body: JSON.stringify({ question, employee_country: "BE", destination_country: "ES", working_days: 8, as_of: "2026-09-30" }),
      });
      if (!response.ok) throw new Error("Resolve could not analyse the question.");
      setResult(await response.json());
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Something went wrong."); }
    finally { setLoading(false); }
  }

  return <main>
    <nav><div className="brand"><span className="mark">R</span>Resolve</div><span className="nav-label">Knowledge trust layer</span><span className="user">Demo consultant · HR scope</span></nav>
    <section className="hero"><p className="eyebrow">SD WORX · TECTONIC HACKATHON</p><h1>Find the answer.<br /><em>Know why it is safe.</em></h1><p className="lede">Resolve ranks knowledge by authority, context, ownership and freshness—not a black-box confidence score.</p></section>
    <section className="workspace">
      <form onSubmit={ask} className="ask"><label htmlFor="question">Ask Resolve</label><div className="ask-row"><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} /><button disabled={loading}>{loading ? "Resolving…" : "Resolve question"}</button></div><p>Context: Belgian employee · working remotely from Spain · 8 working days · 30 Sep 2026</p></form>
      {error && <p className="error">{error} Start the API at port 8000 and try again.</p>}
      {result && <ResultView result={result} />}
      {!result && <div className="empty"><span>01</span><p>Try the prepared scenario to see competing evidence handled transparently.</p></div>}
    </section>
  </main>;
}

function ResultView({ result }: { result: Result }) {
  return <section className="results">
    <div className={`answer ${result.outcome}`}><p className="eyebrow">{result.outcome === "resolved" ? "RESOLVED · HIGH CONFIDENCE" : "SAFE ESCALATION"}</p><h2>{result.answer || result.message}</h2>{result.outcome === "resolved" && <p>One historical conflict was found and excluded because the policy is superseded. Resolve did not use wrong-jurisdiction or ownerless information.</p>}{result.expert && <div className="expert">Recommended expert <strong>{result.expert.name}</strong> · {result.expert.team}</div>}</div>
    {result.dimensions && <div className="dimensions"><h3>Why this answer is trustworthy</h3><div className="dimension-grid">{Object.entries(result.dimensions).map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div></div>}
    <div className="evidence"><div><p className="eyebrow">EVIDENCE REVIEW</p><h3>{result.candidates.length} relevant claims, evaluated in context</h3></div>{result.candidates.map((candidate) => <article key={candidate.source.id} className={candidate.decision}><div className="source-head"><div><DecisionBadge decision={candidate.decision} /><h4>{candidate.source.title}</h4><p>{candidate.source.type.replaceAll("_", " ")} · {candidate.source.country || "No jurisdiction"} · {candidate.source.owner || "No owner"}</p></div></div><blockquote>{candidate.claim}</blockquote><ul>{candidate.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></article>)}</div>
    <footer><span>Next: Scenario B</span> Current authoritative conflicts route to the responsible expert; their resolution becomes durable knowledge in Scenario C.</footer>
  </section>;
}
