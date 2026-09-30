"""Persistence schema for the production adapter.

The running MVP uses a deterministic in-memory repository so the vertical slice
works without cloud credentials. These SQLAlchemy models are the contract for
PostgreSQL + pgvector once ingestion and Gemini embeddings are switched on.
"""
from datetime import date, datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceModel(Base):
    __tablename__ = "sources"
    # Human-readable IDs keep the demo data traceable from a visible source card
    # through to its claim, conflict and expert resolution.
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))
    authority: Mapped[str] = mapped_column(String(30))
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    visibility_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClaimModel(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    statement: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)


class ConflictModel(Base):
    __tablename__ = "conflicts"
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    claim_a_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    claim_b_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    kind: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(20))


class ExpertModel(Base):
    __tablename__ = "experts"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    team: Mapped[str] = mapped_column(String(255))
    specialties: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    countries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class QuestionModel(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(255), index=True)
    question: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResolutionModel(Base):
    __tablename__ = "resolutions"
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    conflict_id: Mapped[str] = mapped_column(ForeignKey("conflicts.id"), unique=True)
    expert_id: Mapped[str] = mapped_column(ForeignKey("experts.id"))
    decision: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
