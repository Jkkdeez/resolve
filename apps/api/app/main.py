from dataclasses import replace
from datetime import date
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .domain import Actor, QuestionRecord, Resolution
from .reasoning import resolve
from .seed import CLAIMS, CONFLICTS, EXPERTS, RESOLUTIONS, SOURCES

app = FastAPI(title="Resolve API", version="0.1.0")


class KnowledgeStore:
    """Replace with the PostgreSQL repository after the demo flow is validated."""
    def __init__(self) -> None:
        self.conflicts = {conflict.id: conflict for conflict in CONFLICTS}
        self.resolutions: dict[str, Resolution] = {resolution.conflict_id: resolution for resolution in RESOLUTIONS}
        self.questions: list[QuestionRecord] = []
        self.lock = Lock()

    def snapshot(self):
        with self.lock:
            return tuple(self.conflicts.values()), tuple(self.resolutions.values())

    def save_resolution(self, conflict_id: str, expert_id: str, decision: str, rationale: str, created_on: date) -> Resolution:
        with self.lock:
            if conflict_id not in self.conflicts:
                raise KeyError(conflict_id)
            resolution = Resolution(f"res-{conflict_id}", conflict_id, expert_id, decision, rationale, created_on)
            self.resolutions[conflict_id] = resolution
            self.conflicts[conflict_id] = replace(self.conflicts[conflict_id], status="resolved")
            return resolution

    def record_question(self, actor_id: str, question: str, country: str, outcome: str, created_on: date) -> QuestionRecord:
        with self.lock:
            record = QuestionRecord(f"q-{len(self.questions) + 1}", actor_id, question, country, outcome, created_on)
            self.questions.append(record)
            return record

    def questions_for(self, actor_id: str) -> tuple[QuestionRecord, ...]:
        with self.lock:
            return tuple(record for record in self.questions if record.actor_id == actor_id)

    def reset(self) -> None:
        """Test-only reset; real deployments use a transaction-scoped repository."""
        with self.lock:
            self.conflicts = {conflict.id: conflict for conflict in CONFLICTS}
            self.resolutions = {resolution.conflict_id: resolution for resolution in RESOLUTIONS}
            self.questions = []


store = KnowledgeStore()


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    employee_country: str = Field(min_length=2, max_length=2)
    destination_country: str | None = Field(default=None, min_length=2, max_length=2)
    working_days: int | None = Field(default=None, ge=1, le=365)
    as_of: date = date(2026, 9, 30)


class ResolutionRequest(BaseModel):
    decision: str = Field(min_length=10, max_length=1000)
    rationale: str = Field(min_length=10, max_length=2000)


def current_actor(x_resolve_user: str | None = Header(default=None), x_resolve_roles: str | None = Header(default=None)) -> Actor:
    # Development adapter. Replace with OIDC verification on Cloud Run; API contracts
    # and access checks deliberately require an actor from day one.
    if not x_resolve_user or not x_resolve_roles:
        raise HTTPException(status_code=401, detail="An authenticated Resolve actor is required.")
    roles = frozenset(role.strip() for role in x_resolve_roles.split(",") if role.strip())
    if not roles:
        raise HTTPException(status_code=403, detail="Actor has no knowledge scopes.")
    return Actor(id=x_resolve_user, roles=roles)


def serialize_candidate(candidate):
    return {
        "claim": candidate.claim.statement,
        "value": candidate.claim.value,
        "source": {"id": candidate.source.id, "title": candidate.source.title, "type": candidate.source.source_type, "owner": candidate.source.owner, "country": candidate.source.country},
        "decision": candidate.decision,
        "reasons": list(candidate.reasons),
    }


def serialize_resolution(resolution: Resolution | None, expert=None):
    if not resolution:
        return None
    return {
        "id": resolution.id,
        "conflict_id": resolution.conflict_id,
        "decision": resolution.decision,
        "rationale": resolution.rationale,
        "created_on": resolution.created_on.isoformat(),
        "expert": {"id": expert.id, "name": expert.name, "team": expert.team} if expert else {"id": resolution.expert_id},
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/questions/answer")
def answer_question(payload: AskRequest, actor: Actor = Depends(current_actor)):
    conflicts, resolutions = store.snapshot()
    result = resolve(actor=actor, question=payload.question, country=payload.employee_country.upper(), on_date=payload.as_of, duration_days=payload.working_days, sources=SOURCES, claims=CLAIMS, conflicts=conflicts, experts=EXPERTS, resolutions=resolutions)
    result["candidates"] = [serialize_candidate(candidate) for candidate in result.get("candidates", [])]
    if result.get("winner"):
        result["winner"] = serialize_candidate(result["winner"])
    if result.get("expert"):
        expert = result["expert"]
        result["expert"] = {"id": expert.id, "name": expert.name, "team": expert.team, "specialties": expert.specialties}
    if result.get("resolution"):
        resolution = result["resolution"]
        expert = next((expert for expert in EXPERTS if expert.id == resolution.expert_id), None)
        result["resolution"] = serialize_resolution(resolution, expert)
    question_event = store.record_question(actor.id, payload.question, payload.employee_country.upper(), result["outcome"], payload.as_of)
    result["question_id"] = question_event.id
    return result


@app.get("/v1/conflicts")
def list_conflicts(actor: Actor = Depends(current_actor)):
    """Return only conflicts whose underlying sources are in the actor's scope."""
    conflicts, resolutions = store.snapshot()
    accessible_source_ids = {source.id for source in SOURCES if source.visibility.value in actor.roles}
    accessible_claim_ids = {claim.id for claim in CLAIMS if claim.source_id in accessible_source_ids}
    return [
        {"id": conflict.id, "kind": conflict.kind, "status": conflict.status, "severity": conflict.severity}
        for conflict in conflicts
        if conflict.claim_a_id in accessible_claim_ids and conflict.claim_b_id in accessible_claim_ids
    ]


@app.get("/v1/knowledge/overview")
def knowledge_overview(actor: Actor = Depends(current_actor)):
    """Permissioned operational view of the ingest → claim → conflict pipeline."""
    conflicts, resolutions = store.snapshot()
    accessible_sources = [source for source in SOURCES if source.visibility.value in actor.roles]
    source_ids = {source.id for source in accessible_sources}
    accessible_claims = [claim for claim in CLAIMS if claim.source_id in source_ids]
    claim_ids = {claim.id for claim in accessible_claims}
    accessible_conflicts = [
        conflict for conflict in conflicts
        if conflict.claim_a_id in claim_ids and conflict.claim_b_id in claim_ids
    ]
    resolution_ids = {resolution.conflict_id for resolution in resolutions}
    return {
        "counts": {
            "sources": len(accessible_sources),
            "claims": len(accessible_claims),
            "open_conflicts": sum(conflict.status == "open" for conflict in accessible_conflicts),
            "human_resolutions": sum(conflict.id in resolution_ids for conflict in accessible_conflicts),
        },
        "stages": [
            {"name": "Ingest", "detail": f"{len(accessible_sources)} permissioned sources", "state": "complete"},
            {"name": "Structure", "detail": f"{len(accessible_claims)} contextual claims", "state": "complete"},
            {"name": "Detect", "detail": f"{sum(conflict.status == 'open' for conflict in accessible_conflicts)} conflict needs review", "state": "attention" if any(conflict.status == "open" for conflict in accessible_conflicts) else "complete"},
            {"name": "Learn", "detail": f"{sum(conflict.id in resolution_ids for conflict in accessible_conflicts)} expert decisions reusable", "state": "complete"},
        ],
        "recent_questions": [
            {"id": record.id, "question": record.question, "outcome": record.outcome, "country": record.country}
            for record in store.questions_for(actor.id)[-4:][::-1]
        ],
    }


@app.post("/v1/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, payload: ResolutionRequest, actor: Actor = Depends(current_actor)):
    # In production this is an OIDC group/entitlement check. Requiring both the
    # expert identity and payroll scope prevents an ordinary consultant resolving
    # a compliance conflict by guessing its ID.
    expert = next((expert for expert in EXPERTS if expert.id == actor.id), None)
    if not expert or "expert" not in actor.roles or "payroll" not in actor.roles:
        raise HTTPException(status_code=403, detail="Only the designated payroll expert can resolve this conflict.")
    conflicts, _ = store.snapshot()
    conflict = next((conflict for conflict in conflicts if conflict.id == conflict_id), None)
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found.")
    if conflict.status == "resolved":
        raise HTTPException(status_code=409, detail="Conflict already has a resolution.")
    if "overtime_premium" not in expert.specialties:
        raise HTTPException(status_code=403, detail="Expert is not assigned to this knowledge domain.")
    resolution = store.save_resolution(conflict_id, expert.id, payload.decision, payload.rationale, date.today())
    return serialize_resolution(resolution, expert)
