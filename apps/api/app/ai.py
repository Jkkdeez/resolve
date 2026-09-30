"""Bounded AI integration seam for Google Cloud Vertex AI.

The trust engine never delegates permission, jurisdiction, date or authority
decisions to a model. An adapter can use Gemini only to propose structured
claims and semantic candidates, which remain subject to deterministic checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractedClaim:
    topic: str
    statement: str
    country: str | None
    effective_from: str | None
    effective_until: str | None


class KnowledgeModel(Protocol):
    def extract_claims(self, content: str) -> list[ExtractedClaim]: ...
    def embed(self, content: str) -> list[float]: ...


class VertexGeminiAdapter:
    """Future Google Cloud adapter, intentionally not invoked in the MVP.

    Wire `google-genai` / Vertex credentials here after a project is available.
    Keep model outputs schema-validated and store proposed claims as untrusted
    until they are reviewed or corroborated.
    """
    def __init__(self, project: str, location: str, model: str) -> None:
        self.project = project
        self.location = location
        self.model = model

    def extract_claims(self, content: str) -> list[ExtractedClaim]:
        raise NotImplementedError("Configure the Vertex client when GCP credentials are available.")

    def embed(self, content: str) -> list[float]:
        raise NotImplementedError("Configure a Vertex embedding model when GCP credentials are available.")
