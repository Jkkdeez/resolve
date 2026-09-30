import unittest
from datetime import date

from app.domain import Actor, Resolution
from app.reasoning import resolve
from app.seed import CLAIMS, CONFLICTS, EXPERTS, RESOLUTIONS, SOURCES


class ResolveScenarioTests(unittest.TestCase):
    def setUp(self):
        self.actor = Actor("consultant-1", frozenset({"hr", "internal"}))

    def test_scenario_a_prefers_current_belgian_owned_policy(self):
        result = resolve(actor=self.actor, question="Can a Belgian employee work remotely from Spain for eight working days?", country="BE", on_date=date(2026, 9, 30), duration_days=8, sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, experts=EXPERTS, resolutions=RESOLUTIONS)
        self.assertEqual(result["outcome"], "resolved")
        self.assertIn("No manager approval", result["answer"])
        self.assertEqual(result["winner"].source.id, "src-be-remote-2026")
        decisions = {candidate.source.id: candidate.decision for candidate in result["candidates"]}
        self.assertEqual(decisions["src-nl-remote-2026"], "rejected")
        self.assertEqual(decisions["src-be-handbook-2024"], "rejected")
        self.assertEqual(decisions["src-shared-pdf"], "downranked")

    def test_scenario_b_escalates_current_conflict_to_expert(self):
        result = resolve(actor=Actor("payroll-1", frozenset({"payroll"})), question="How should overtime be calculated for this Belgian customer?", country="BE", on_date=date(2026, 9, 30), duration_days=None, sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, experts=EXPERTS, resolutions=RESOLUTIONS)
        self.assertEqual(result["outcome"], "escalate")
        self.assertEqual(result["expert"].name, "Anna De Smet")

    def test_retrieval_does_not_bypass_source_scope(self):
        result = resolve(actor=Actor("hr-1", frozenset({"hr"})), question="How should overtime be calculated for this Belgian customer?", country="BE", on_date=date(2026, 9, 30), duration_days=None, sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, experts=EXPERTS, resolutions=RESOLUTIONS)
        self.assertEqual(result["outcome"], "escalate")
        self.assertEqual(result["candidates"], [])

    def test_scenario_c_uses_human_resolution_before_source_ranking(self):
        decision = "Apply the 200% premium for this customer configuration; its signed customer agreement controls."
        result = resolve(actor=Actor("payroll-1", frozenset({"payroll"})), question="How should overtime be calculated for this Belgian customer?", country="BE", on_date=date(2026, 9, 30), duration_days=None, sources=SOURCES, claims=CLAIMS, conflicts=CONFLICTS, experts=EXPERTS, resolutions=(Resolution("res-overtime", "conf-overtime-current", "exp-anna", decision, "Customer agreement verified.", date(2026, 9, 30)),))
        self.assertEqual(result["outcome"], "resolved")
        self.assertEqual(result["answer"], decision)
        self.assertEqual(result["resolution"].expert_id, "exp-anna")


if __name__ == "__main__":
    unittest.main()
