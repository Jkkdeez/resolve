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


if __name__ == "__main__":
    unittest.main()
