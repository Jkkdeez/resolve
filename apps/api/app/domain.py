from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Authority(StrEnum):
    OFFICIAL = "official"
    COLLABORATIVE = "collaborative"
    UNVERIFIED = "unverified"


class Visibility(StrEnum):
    PAYROLL = "payroll"
    HR = "hr"
    INTERNAL = "internal"


@dataclass(frozen=True)
class Actor:
    id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    source_type: str
    authority: Authority
    owner: str | None
    country: str | None
    effective_from: date | None
    effective_until: date | None
    visibility: Visibility
    content: str
    superseded_by: str | None = None


@dataclass(frozen=True)
class Claim:
    id: str
    source_id: str
    topic: str
    statement: str
    country: str | None
    effective_from: date | None
    effective_until: date | None
    value: int | None = None


@dataclass(frozen=True)
class Conflict:
    id: str
    claim_a_id: str
    claim_b_id: str
    kind: str
    status: str
    severity: str


@dataclass(frozen=True)
class Expert:
    id: str
    name: str
    team: str
    specialties: tuple[str, ...]
    countries: tuple[str, ...]


@dataclass(frozen=True)
class Resolution:
    id: str
    conflict_id: str
    expert_id: str
    decision: str
    rationale: str
    created_on: date
