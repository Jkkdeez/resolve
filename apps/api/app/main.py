from datetime import date
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from .domain import Actor, Authority, Claim, Resolution, Source, Visibility
from .pipeline import extract_claims
from .repository import InMemoryKnowledgeStore, PostgresKnowledgeStore
from .reasoning import resolve
from .seed import CLAIMS, CONFLICTS, EXPERTS, RESOLUTIONS, SOURCES

app = FastAPI(title="Resolve API", version="0.1.0")


database_url = os.getenv("DATABASE_URL")
store = (
    PostgresKnowledgeStore(database_url, sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, experts=EXPERTS, resolutions=RESOLUTIONS)
    if database_url
    else InMemoryKnowledgeStore(sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, resolutions=RESOLUTIONS)
)


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    employee_country: str = Field(min_length=2, max_length=2)
    destination_country: str | None = Field(default=None, min_length=2, max_length=2)
    working_days: int | None = Field(default=None, ge=1, le=365)
    as_of: date = date(2026, 9, 30)


class ResolutionRequest(BaseModel):
    decision: str = Field(min_length=10, max_length=1000)
    rationale: str = Field(min_length=10, max_length=2000)


class SourceIngestRequest(BaseModel):
    """Generic connector payload; Teams, Drive and SD Worx adapters map here later."""
    title: str = Field(min_length=3, max_length=255)
    source_type: str = Field(min_length=3, max_length=50)
    content: str = Field(min_length=20, max_length=50_000)
    authority: str = Field(default="official")
    owner: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    effective_from: date | None = None
    effective_until: date | None = None
    visibility: str = Field(default="internal")

    @field_validator("authority")
    @classmethod
    def valid_authority(cls, value: str) -> str:
        if value not in {item.value for item in Authority}:
            raise ValueError("authority must be official, collaborative or unverified")
        return value

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, value: str) -> str:
        if value not in {item.value for item in Visibility}:
            raise ValueError("visibility must be hr, payroll or internal")
        return value

    @field_validator("country")
    @classmethod
    def uppercase_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value


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
    sources, claims, conflicts, resolutions = store.snapshot()
    result = resolve(actor=actor, question=payload.question, country=payload.employee_country.upper(), on_date=payload.as_of, duration_days=payload.working_days, sources=sources, claims=claims, conflicts=conflicts, experts=EXPERTS, resolutions=resolutions)
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
    sources, claims, conflicts, _ = store.snapshot()
    accessible_source_ids = {source.id for source in sources if source.visibility.value in actor.roles}
    accessible_claim_ids = {claim.id for claim in claims if claim.source_id in accessible_source_ids}
    return [
        {"id": conflict.id, "kind": conflict.kind, "status": conflict.status, "severity": conflict.severity}
        for conflict in conflicts
        if conflict.claim_a_id in accessible_claim_ids and conflict.claim_b_id in accessible_claim_ids
    ]


@app.get("/v1/knowledge/overview")
def knowledge_overview(actor: Actor = Depends(current_actor)):
    """Permissioned operational view of the ingest → claim → conflict pipeline."""
    sources, claims, conflicts, resolutions = store.snapshot()
    accessible_sources = [source for source in sources if source.visibility.value in actor.roles]
    source_ids = {source.id for source in accessible_sources}
    accessible_claims = [claim for claim in claims if claim.source_id in source_ids]
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


@app.post("/v1/sources/ingest", status_code=201)
def ingest_source(payload: SourceIngestRequest, actor: Actor = Depends(current_actor)):
    """Ingest one governed source through the shared connector contract."""
    if "knowledge_admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Only a knowledge administrator can ingest organisational sources.")
    if payload.effective_until and payload.effective_from and payload.effective_until < payload.effective_from:
        raise HTTPException(status_code=422, detail="effective_until cannot precede effective_from.")
    source = Source(
        id=f"src-{uuid4().hex[:12]}",
        title=payload.title,
        source_type=payload.source_type,
        authority=Authority(payload.authority),
        owner=payload.owner,
        country=payload.country,
        effective_from=payload.effective_from,
        effective_until=payload.effective_until,
        visibility=Visibility(payload.visibility),
        content=payload.content,
    )
    claims = extract_claims(source)
    conflicts = store.ingest(source, claims)
    return {
        "source": {"id": source.id, "title": source.title, "visibility": source.visibility.value, "authority": source.authority.value},
        "claims": [{"id": claim.id, "topic": claim.topic, "statement": claim.statement, "value": claim.value} for claim in claims],
        "conflicts": [{"id": conflict.id, "kind": conflict.kind, "severity": conflict.severity} for conflict in conflicts],
    }


@app.post("/v1/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, payload: ResolutionRequest, actor: Actor = Depends(current_actor)):
    # In production this is an OIDC group/entitlement check. Requiring both the
    # expert identity and payroll scope prevents an ordinary consultant resolving
    # a compliance conflict by guessing its ID.
    expert = next((expert for expert in EXPERTS if expert.id == actor.id), None)
    if not expert or "expert" not in actor.roles or "payroll" not in actor.roles:
        raise HTTPException(status_code=403, detail="Only the designated payroll expert can resolve this conflict.")
    _, _, conflicts, _ = store.snapshot()
    conflict = next((conflict for conflict in conflicts if conflict.id == conflict_id), None)
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found.")
    if conflict.status == "resolved":
        raise HTTPException(status_code=409, detail="Conflict already has a resolution.")
    if "overtime_premium" not in expert.specialties:
        raise HTTPException(status_code=403, detail="Expert is not assigned to this knowledge domain.")
    resolution = store.save_resolution(conflict_id, expert.id, payload.decision, payload.rationale, date.today())
    return serialize_resolution(resolution, expert)
