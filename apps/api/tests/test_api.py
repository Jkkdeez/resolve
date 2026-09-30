import unittest

from fastapi.testclient import TestClient

from app.main import app, store


class ApiSecurityAndResolutionTests(unittest.TestCase):
    def setUp(self):
        store.reset()
        self.client = TestClient(app)

    def test_question_requires_an_authenticated_actor(self):
        response = self.client.post(
            "/v1/questions/answer",
            json={"question": "Can a Belgian employee work remotely from Spain?", "employee_country": "BE"},
        )
        self.assertEqual(response.status_code, 401)

    def test_only_assigned_expert_can_create_reusable_resolution(self):
        forbidden = self.client.post(
            "/v1/conflicts/conf-overtime-current/resolve",
            headers={"x-resolve-user": "ordinary-consultant", "x-resolve-roles": "payroll"},
            json={"decision": "Use the 200% agreement.", "rationale": "A customer agreement says so."},
        )
        self.assertEqual(forbidden.status_code, 403)

        saved = self.client.post(
            "/v1/conflicts/conf-overtime-current/resolve",
            headers={"x-resolve-user": "exp-anna", "x-resolve-roles": "payroll,expert"},
            json={
                "decision": "Apply the 200% premium for this customer configuration; its signed customer agreement controls.",
                "rationale": "The customer agreement was verified against the configuration.",
            },
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["expert"]["id"], "exp-anna")

        answer = self.client.post(
            "/v1/questions/answer",
            headers={"x-resolve-user": "payroll-consultant", "x-resolve-roles": "payroll"},
            json={"question": "How should overtime be calculated for this Belgian customer?", "employee_country": "BE"},
        )
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["outcome"], "resolved")
        self.assertIn("200%", answer.json()["answer"])
        self.assertEqual(answer.json()["resolution"]["expert"]["id"], "exp-anna")

    def test_pipeline_overview_is_scoped_and_tracks_question_events(self):
        headers = {"x-resolve-user": "demo-consultant", "x-resolve-roles": "hr,internal"}
        asked = self.client.post(
            "/v1/questions/answer",
            headers=headers,
            json={"question": "Can a Belgian employee work remotely from Spain?", "employee_country": "BE"},
        )
        self.assertEqual(asked.status_code, 200)

        overview = self.client.get("/v1/knowledge/overview", headers=headers)
        self.assertEqual(overview.status_code, 200)
        body = overview.json()
        self.assertEqual(body["counts"]["sources"], 5)
        self.assertEqual(body["counts"]["open_conflicts"], 0)
        self.assertEqual(body["recent_questions"][0]["id"], asked.json()["question_id"])

    def test_ingest_extracts_claim_and_opens_a_governed_conflict(self):
        denied = self.client.post(
            "/v1/sources/ingest",
            headers={"x-resolve-user": "ordinary-consultant", "x-resolve-roles": "payroll"},
            json={"title": "Customer addendum", "source_type": "signed_agreement", "content": "Qualifying overtime receives a 175% premium.", "country": "BE", "effective_from": "2026-01-01", "visibility": "payroll"},
        )
        self.assertEqual(denied.status_code, 403)

        ingested = self.client.post(
            "/v1/sources/ingest",
            headers={"x-resolve-user": "knowledge-steward", "x-resolve-roles": "payroll,knowledge_admin"},
            json={"title": "Customer addendum", "source_type": "signed_agreement", "content": "Qualifying overtime receives a 175% premium.", "country": "BE", "effective_from": "2026-01-01", "visibility": "payroll", "owner": "Payroll Compliance Belgium"},
        )
        self.assertEqual(ingested.status_code, 201)
        self.assertEqual(ingested.json()["claims"][0]["value"], 175)
        self.assertGreaterEqual(len(ingested.json()["conflicts"]), 1)


if __name__ == "__main__":
    unittest.main()
