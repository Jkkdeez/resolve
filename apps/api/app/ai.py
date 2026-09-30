"""Bounded AI integration seam for Google Cloud Vertex AI.

The trust engine never delegates permission, jurisdiction, date or authority
decisions to a model. An adapter can use Gemini only to propose structured
claims and semantic candidates, which remain subject to deterministic checks.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
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
    """Optional Vertex AI adapter with deliberately bounded responsibilities."""
    def __init__(self, project: str, location: str, model: str) -> None:
        self.project = project
        self.location = location
        self.model = model

    def _client(self):
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install google-genai and configure Google Application Default Credentials.") from exc
        return genai.Client(vertexai=True, project=self.project, location=self.location)

    def extract_claims(self, content: str) -> list[ExtractedClaim]:
        prompt = """Extract policy claims from this organisational source. Return JSON only: an array of objects with topic, statement, country, effective_from, effective_until. Use null when absent. Do not infer authority, ownership or access scope. Source:\n\n""" + content
        response = self._client().models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        raw = json.loads(response.text or "[]")
        if not isinstance(raw, list):
            raise ValueError("Vertex claim extraction returned a non-list response.")
        return [ExtractedClaim(
            topic=str(item["topic"]),
            statement=str(item["statement"]),
            country=item.get("country"),
            effective_from=item.get("effective_from"),
            effective_until=item.get("effective_until"),
        ) for item in raw if isinstance(item, dict) and item.get("topic") and item.get("statement")]

    def embed(self, content: str) -> list[float]:
        response = self._client().models.embed_content(model="text-embedding-004", contents=content)
        return list(response.embeddings[0].values)
