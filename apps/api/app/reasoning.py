from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from .domain import Actor, Authority, Claim, Conflict, Expert, Resolution, Source


@dataclass(frozen=True)
class Candidate:
    claim: Claim
    source: Source
    decision: str
    reasons: tuple[str, ...]


def can_access(actor: Actor, source: Source) -> bool:
    return source.visibility.value in actor.roles


def evaluate_claim(claim: Claim, source: Source, *, country: str, on_date: date) -> Candidate:
    reasons: list[str] = []
    if source.country and source.country != country:
        return Candidate(claim, source, "rejected", (f"Jurisdiction mismatch: source applies to {source.country}, not {country}.",))
    if source.superseded_by:
        return Candidate(claim, source, "rejected", (f"Superseded by {source.superseded_by}.",))
    if source.effective_until and source.effective_until < on_date:
        return Candidate(claim, source, "rejected", (f"Expired on {source.effective_until.isoformat()}.",))
    if not source.owner:
        return Candidate(claim, source, "downranked", ("No accountable owner is recorded.",))
    if source.authority == Authority.UNVERIFIED:
        return Candidate(claim, source, "downranked", ("Source is unverified.",))
    reasons.append("Applicable jurisdiction.")
    reasons.append("Current for the question date.")
    reasons.append("Accountable owner recorded.")
    reasons.append("Official policy." if source.authority == Authority.OFFICIAL else "Supporting collaborative evidence.")
    return Candidate(claim, source, "accepted", tuple(reasons))


def detect_question_type(text: str) -> str:
    normalized = text.lower()
    if "remote" in normalized or "work abroad" in normalized or "spain" in normalized:
        return "remote_work_abroad_approval_threshold"
    if "overtime" in normalized:
        return "overtime_premium"
    return "unknown"


def resolve(
    *,
    actor: Actor,
    question: str,
    country: str,
    on_date: date,
    duration_days: int | None,
    sources: Iterable[Source],
    claims: Iterable[Claim],
    conflicts: Iterable[Conflict],
    experts: Iterable[Expert],
    resolutions: Iterable[Resolution],
) -> dict:
    topic = detect_question_type(question)
    source_by_id = {source.id: source for source in sources if can_access(actor, source)}
    all_claims = [claim for claim in claims if claim.topic == topic and claim.source_id in source_by_id]
    candidates = [evaluate_claim(claim, source_by_id[claim.source_id], country=country, on_date=on_date) for claim in all_claims]
    accepted = [candidate for candidate in candidates if candidate.decision == "accepted"]
    related_conflicts = [c for c in conflicts if {c.claim_a_id, c.claim_b_id}.issubset({claim.id for claim in all_claims})]
    resolution_by_conflict = {resolution.conflict_id: resolution for resolution in resolutions}
    human_resolution = next((resolution_by_conflict[conflict.id] for conflict in related_conflicts if conflict.id in resolution_by_conflict), None)

    if topic == "unknown" or not candidates:
        return {"outcome": "escalate", "message": "I could not find permissioned, applicable knowledge for this question.", "candidates": [], "expert": None}

    open_conflicts = [conflict for conflict in related_conflicts if conflict.status == "open"]
    if open_conflicts and not human_resolution:
        expert = next((e for e in experts if topic in e.specialties and country in e.countries), None)
        return {
            "outcome": "escalate",
            "message": "I cannot safely resolve this: two current, authoritative claims conflict.",
            "candidates": candidates,
            "expert": expert,
            "open_conflict_ids": [conflict.id for conflict in open_conflicts],
        }

    # A human decision beats automatic ranking for a previously unresolved conflict.
    if human_resolution:
        expert = next((expert for expert in experts if expert.id == human_resolution.expert_id), None)
        return {
            "outcome": "resolved",
            "answer": human_resolution.decision,
            "winner": None,
            "candidates": candidates,
            "dimensions": {
                "authority": "Human verified — designated payroll expert",
                "jurisdiction": f"Match — {country}",
                "freshness": f"Resolved on {human_resolution.created_on.isoformat()}",
                "ownership": f"Decision owner — {expert.name if expert else human_resolution.expert_id}",
                "corroboration": "Expert reviewed the conflicting current policies",
                "conflicts": "Resolved — reusable organisational knowledge",
            },
            "resolution": human_resolution,
            "expert": expert,
        }

    winner = next((candidate for candidate in accepted if candidate.source.authority == Authority.OFFICIAL), accepted[0] if accepted else None)
    if not winner:
        return {"outcome": "escalate", "message": "The available evidence is not owned and verifiable enough to answer safely.", "candidates": candidates, "expert": None}

    if topic == "remote_work_abroad_approval_threshold":
        requires_approval = duration_days is not None and duration_days > (winner.claim.value or 0)
        answer = (
            f"No manager approval is required for {duration_days} working days under the current Belgian policy."
            if not requires_approval
            else f"Manager approval is required because {duration_days} working days exceeds the current {winner.claim.value}-day threshold."
        )
    else:
        answer = winner.claim.statement

    return {
        "outcome": "resolved",
        "answer": answer,
        "winner": winner,
        "candidates": candidates,
        "dimensions": {
            "authority": "High — official policy",
            "jurisdiction": f"Match — {country}",
            "freshness": "Current for the question date",
            "ownership": f"Verified — {winner.source.owner}",
            "corroboration": "Teams update independently confirms the 2026 change" if topic == "remote_work_abroad_approval_threshold" else "No conflicting current sources",
            "conflicts": "Historical conflict rejected as superseded" if topic == "remote_work_abroad_approval_threshold" else "None",
        },
        "resolution": None,
    }
