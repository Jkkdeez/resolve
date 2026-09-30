"""Persistence schema for the production adapter.

The running MVP uses a deterministic in-memory repository so the vertical slice
works without cloud credentials. These SQLAlchemy models are the contract for
PostgreSQL + pgvector once ingestion and Gemini embeddings are switched on.
"""
from datetime import date, datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceModel(Base):
    __tablename__ = "sources"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))
    authority: Mapped[str] = mapped_column(String(30))
    owner_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    visibility_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClaimModel(Base):
    __tablename__ = "claims"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    statement: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)


class ConflictModel(Base):
    __tablename__ = "conflicts"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_a_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"))
    claim_b_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id"))
    kind: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(20))


class ExpertModel(Base):
    __tablename__ = "experts"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    team: Mapped[str] = mapped_column(String(255))
    specialties: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    countries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class QuestionModel(Base):
    __tablename__ = "questions"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_id: Mapped[str] = mapped_column(String(255), index=True)
    question: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResolutionModel(Base):
    __tablename__ = "resolutions"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conflict_id: Mapped[UUID] = mapped_column(ForeignKey("conflicts.id"), unique=True)
    expert_id: Mapped[UUID] = mapped_column(ForeignKey("experts.id"))
    decision: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
