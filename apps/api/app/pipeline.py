"""Deterministic source-to-claim extraction for the connector-ready ingest path."""
from __future__ import annotations

import re
from datetime import date
from uuid import uuid4

from .domain import Claim, Source


REMOTE_THRESHOLD = re.compile(r"(?:above|exceed(?:s|ing)?|more than)\s+(\d+)\s+working\s+days", re.IGNORECASE)
OVERTIME_PREMIUM = re.compile(r"(?:overtime|premium).*?(\d{3})\s*%|(?:\b)(\d{3})\s*%.*?(?:overtime|premium)", re.IGNORECASE | re.DOTALL)


def extract_claims(source: Source) -> tuple[Claim, ...]:
    """Produce schema-bound claims from common policy language.

    This deterministic baseline is deliberately usable with no cloud credential.
    Gemini may later propose additional candidates, but every candidate must pass
    the same validation and conflict pipeline.
    """
    content = source.content
    normalized = content.lower()
    claims: list[Claim] = []
    remote_match = REMOTE_THRESHOLD.search(content)
    if remote_match and ("remote" in normalized or "work abroad" in normalized):
        threshold = int(remote_match.group(1))
        claims.append(Claim(
            id=f"clm-{uuid4().hex[:12]}",
            source_id=source.id,
            topic="remote_work_abroad_approval_threshold",
            statement=f"Approval is required above {threshold} working days.",
            country=source.country,
            effective_from=source.effective_from,
            effective_until=source.effective_until,
            value=threshold,
        ))
    overtime_match = OVERTIME_PREMIUM.search(content)
    if overtime_match and "overtime" in normalized:
        premium = int(overtime_match.group(1) or overtime_match.group(2))
        claims.append(Claim(
            id=f"clm-{uuid4().hex[:12]}",
            source_id=source.id,
            topic="overtime_premium",
            statement=f"Qualifying overtime gets a {premium}% premium.",
            country=source.country,
            effective_from=source.effective_from,
            effective_until=source.effective_until,
            value=premium,
        ))
    return tuple(claims)
