from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .domain import Actor
from .reasoning import resolve
from .seed import CLAIMS, CONFLICTS, EXPERTS, RESOLUTIONS, SOURCES

app = FastAPI(title="Resolve API", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    employee_country: str = Field(min_length=2, max_length=2)
    destination_country: str | None = Field(default=None, min_length=2, max_length=2)
    working_days: int | None = Field(default=None, ge=1, le=365)
    as_of: date = date(2026, 9, 30)


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/questions/answer")
def answer_question(payload: AskRequest, actor: Actor = Depends(current_actor)):
    result = resolve(actor=actor, question=payload.question, country=payload.employee_country.upper(), on_date=payload.as_of, duration_days=payload.working_days, sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, experts=EXPERTS, resolutions=RESOLUTIONS)
    result["candidates"] = [serialize_candidate(candidate) for candidate in result.get("candidates", [])]
    if result.get("winner"):
        result["winner"] = serialize_candidate(result["winner"])
    if result.get("expert"):
        expert = result["expert"]
        result["expert"] = {"id": expert.id, "name": expert.name, "team": expert.team, "specialties": expert.specialties}
    return result
