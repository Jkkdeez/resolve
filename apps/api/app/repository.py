"""Repository adapters for Resolve's governed knowledge graph.

The in-memory adapter keeps the hackathon demo one-command reproducible. Set
DATABASE_URL to activate the PostgreSQL + pgvector adapter without changing the
API or trust engine.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from threading import Lock
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .domain import Authority, Claim, Conflict, Expert, QuestionRecord, Resolution, Source, Visibility
from .models import Base, ClaimModel, ConflictModel, ExpertModel, QuestionModel, ResolutionModel, SourceModel


def detect_conflicts(new_claims: tuple[Claim, ...], new_source: Source, sources: tuple[Source, ...], claims: tuple[Claim, ...]) -> tuple[Conflict, ...]:
    """Detect only actionable, current official-policy contradictions.

    Semantic similarity can propose candidates in the future, but opening a
    conflict remains deterministic: same topic/country, different values and
    two official sources.
    """
    source_by_id = {source.id: source for source in sources}
    found: list[Conflict] = []
    for candidate in new_claims:
        if candidate.value is None or new_source.authority != Authority.OFFICIAL:
            continue
        for existing in claims:
            existing_source = source_by_id.get(existing.source_id)
            if not existing_source or existing_source.authority != Authority.OFFICIAL:
                continue
            if existing.topic != candidate.topic or existing.country != candidate.country or existing.value == candidate.value:
                continue
            if existing_source.effective_until and existing_source.effective_until < date.today():
                continue
            pair = "-".join(sorted((existing.id, candidate.id)))
            found.append(Conflict(f"conf-{pair}", existing.id, candidate.id, "current_policy_conflict", "open", "high"))
    return tuple(found)


class InMemoryKnowledgeStore:
    def __init__(self, *, sources: tuple[Source, ...], claims: tuple[Claim, ...], conflicts: tuple[Conflict, ...], resolutions: tuple[Resolution, ...]) -> None:
        self._seed = (sources, claims, conflicts, resolutions)
        self.lock = Lock()
        self.reset()

    def reset(self) -> None:
        sources, claims, conflicts, resolutions = self._seed
        with self.lock:
            self.sources = {source.id: source for source in sources}
            self.claims = {claim.id: claim for claim in claims}
            self.conflicts = {conflict.id: conflict for conflict in conflicts}
            self.resolutions = {resolution.conflict_id: resolution for resolution in resolutions}
            self.questions: list[QuestionRecord] = []

    def snapshot(self) -> tuple[tuple[Source, ...], tuple[Claim, ...], tuple[Conflict, ...], tuple[Resolution, ...]]:
        with self.lock:
            return tuple(self.sources.values()), tuple(self.claims.values()), tuple(self.conflicts.values()), tuple(self.resolutions.values())

    def save_resolution(self, conflict_id: str, expert_id: str, decision: str, rationale: str, created_on: date) -> Resolution:
        with self.lock:
            if conflict_id not in self.conflicts:
                raise KeyError(conflict_id)
            resolution = Resolution(f"res-{conflict_id}", conflict_id, expert_id, decision, rationale, created_on)
            self.resolutions[conflict_id] = resolution
            conflict = self.conflicts[conflict_id]
            self.conflicts[conflict_id] = Conflict(conflict.id, conflict.claim_a_id, conflict.claim_b_id, conflict.kind, "resolved", conflict.severity)
            return resolution

    def record_question(self, actor_id: str, question: str, country: str, outcome: str, created_on: date) -> QuestionRecord:
        with self.lock:
            record = QuestionRecord(f"q-{len(self.questions) + 1}", actor_id, question, country, outcome, created_on)
            self.questions.append(record)
            return record

    def questions_for(self, actor_id: str) -> tuple[QuestionRecord, ...]:
        with self.lock:
            return tuple(record for record in self.questions if record.actor_id == actor_id)

    def ingest(self, source: Source, claims: tuple[Claim, ...]) -> tuple[Conflict, ...]:
        with self.lock:
            conflicts = detect_conflicts(claims, source, tuple(self.sources.values()), tuple(self.claims.values()))
            self.sources[source.id] = source
            self.claims.update({claim.id: claim for claim in claims})
            self.conflicts.update({conflict.id: conflict for conflict in conflicts})
            return conflicts


class PostgresKnowledgeStore:
    """Durable PostgreSQL adapter used when DATABASE_URL is configured."""
    def __init__(self, database_url: str, *, sources: tuple[Source, ...], claims: tuple[Claim, ...], conflicts: tuple[Conflict, ...], experts: tuple[Expert, ...], resolutions: tuple[Resolution, ...]) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.seed(sources, claims, conflicts, experts, resolutions)

    def seed(self, sources: tuple[Source, ...], claims: tuple[Claim, ...], conflicts: tuple[Conflict, ...], experts: tuple[Expert, ...], resolutions: tuple[Resolution, ...]) -> None:
        with Session(self.engine) as session:
            if session.scalar(select(SourceModel.id).limit(1)):
                return
            session.add_all([SourceModel(id=source.id, title=source.title, source_type=source.source_type, authority=source.authority.value, owner=source.owner, country=source.country, effective_from=source.effective_from, effective_until=source.effective_until, visibility_roles=[source.visibility.value], content=source.content, embedding=None) for source in sources])
            session.flush()
            session.add_all([ClaimModel(id=claim.id, source_id=claim.source_id, topic=claim.topic, statement=claim.statement, country=claim.country, effective_from=claim.effective_from, effective_until=claim.effective_until, value=claim.value, embedding=None) for claim in claims])
            session.flush()
            session.add_all([ConflictModel(id=conflict.id, claim_a_id=conflict.claim_a_id, claim_b_id=conflict.claim_b_id, kind=conflict.kind, status=conflict.status, severity=conflict.severity) for conflict in conflicts])
            session.add_all([ExpertModel(id=expert.id, name=expert.name, team=expert.team, specialties=list(expert.specialties), countries=list(expert.countries)) for expert in experts])
            session.flush()
            session.add_all([ResolutionModel(id=resolution.id, conflict_id=resolution.conflict_id, expert_id=resolution.expert_id, decision=resolution.decision, rationale=resolution.rationale, created_at=datetime.combine(resolution.created_on, datetime.min.time(), tzinfo=timezone.utc)) for resolution in resolutions])
            session.commit()

    def snapshot(self) -> tuple[tuple[Source, ...], tuple[Claim, ...], tuple[Conflict, ...], tuple[Resolution, ...]]:
        with Session(self.engine) as session:
            sources = tuple(Source(row.id, row.title, row.source_type, Authority(row.authority), row.owner, row.country, row.effective_from, row.effective_until, Visibility(row.visibility_roles[0]), row.content) for row in session.scalars(select(SourceModel)).all())
            claims = tuple(Claim(row.id, row.source_id, row.topic, row.statement, row.country, row.effective_from, row.effective_until, row.value) for row in session.scalars(select(ClaimModel)).all())
            conflicts = tuple(Conflict(row.id, row.claim_a_id, row.claim_b_id, row.kind, row.status, row.severity) for row in session.scalars(select(ConflictModel)).all())
            resolutions = tuple(Resolution(row.id, row.conflict_id, row.expert_id, row.decision, row.rationale, row.created_at.date()) for row in session.scalars(select(ResolutionModel)).all())
            return sources, claims, conflicts, resolutions

    def save_resolution(self, conflict_id: str, expert_id: str, decision: str, rationale: str, created_on: date) -> Resolution:
        with Session(self.engine) as session:
            conflict = session.get(ConflictModel, conflict_id)
            if not conflict:
                raise KeyError(conflict_id)
            resolution = Resolution(f"res-{conflict_id}", conflict_id, expert_id, decision, rationale, created_on)
            session.merge(ResolutionModel(id=resolution.id, conflict_id=conflict_id, expert_id=expert_id, decision=decision, rationale=rationale, created_at=datetime.combine(created_on, datetime.min.time(), tzinfo=timezone.utc)))
            conflict.status = "resolved"
            session.commit()
            return resolution

    def record_question(self, actor_id: str, question: str, country: str, outcome: str, created_on: date) -> QuestionRecord:
        record = QuestionRecord(f"q-{uuid4().hex[:12]}", actor_id, question, country, outcome, created_on)
        with Session(self.engine) as session:
            session.add(QuestionModel(id=record.id, actor_id=actor_id, question=question, context={"country": country}, outcome=outcome, created_at=datetime.combine(created_on, datetime.min.time(), tzinfo=timezone.utc)))
            session.commit()
        return record

    def questions_for(self, actor_id: str) -> tuple[QuestionRecord, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(select(QuestionModel).where(QuestionModel.actor_id == actor_id).order_by(QuestionModel.created_at)).all()
            return tuple(QuestionRecord(row.id, row.actor_id, row.question, row.context.get("country", ""), row.outcome, row.created_at.date()) for row in rows)

    def ingest(self, source: Source, claims: tuple[Claim, ...]) -> tuple[Conflict, ...]:
        sources, existing_claims, _, _ = self.snapshot()
        conflicts = detect_conflicts(claims, source, sources, existing_claims)
        with Session(self.engine) as session:
            session.add(SourceModel(id=source.id, title=source.title, source_type=source.source_type, authority=source.authority.value, owner=source.owner, country=source.country, effective_from=source.effective_from, effective_until=source.effective_until, visibility_roles=[source.visibility.value], content=source.content, embedding=None))
            session.flush()
            session.add_all([ClaimModel(id=claim.id, source_id=claim.source_id, topic=claim.topic, statement=claim.statement, country=claim.country, effective_from=claim.effective_from, effective_until=claim.effective_until, value=claim.value, embedding=None) for claim in claims])
            session.flush()
            session.add_all([ConflictModel(id=conflict.id, claim_a_id=conflict.claim_a_id, claim_b_id=conflict.claim_b_id, kind=conflict.kind, status=conflict.status, severity=conflict.severity) for conflict in conflicts])
            session.commit()
        return conflicts
