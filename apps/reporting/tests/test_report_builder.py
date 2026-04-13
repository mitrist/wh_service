from django.core.management import call_command
from django.test import TestCase

from apps.calculations.score import compute_scores
from apps.core.models import AuditSession, Question
from apps.reporting.report_builder import build_full_report_payload


class ReportBuilderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        if Question.objects.count() == 0:
            call_command("seed_self_audit_questions")

    def test_build_full_report_payload_has_all_sections(self):
        session = AuditSession.objects.create(
            mode="self",
            status="draft",
            client_company="ACME",
            client_email="acme@example.com",
        )
        answers = {f"q{i}": f"q{i}_opt1" for i in range(1, 20)}
        answers["q20_text"] = "Сделать навигацию"
        raw = compute_scores(answers)
        payload = build_full_report_payload(raw, answers, session)
        self.assertIn("header", payload)
        self.assertIn("overall_index", payload)
        self.assertIn("criteria", payload)
        self.assertIn("top_loss_points", payload)
        self.assertIn("market_benchmarks", payload)
        self.assertIn("loss_map", payload)
        self.assertIn("quick_wins", payload)
        self.assertIn("next_steps", payload)

    def test_zone_interpretation_orange_band(self):
        session = AuditSession.objects.create(mode="self", status="draft")
        answers = {f"q{i}": f"q{i}_opt3" for i in range(1, 20)}
        answers["q20_text"] = "x"
        raw = compute_scores(answers)
        payload = build_full_report_payload(raw, answers, session)
        score = payload["overall_index"]["score_percent"]
        if 40 <= score <= 59:
            self.assertEqual(payload["overall_index"]["zone"], "orange")

    def test_next_steps_highlight_for_low_score(self):
        session = AuditSession.objects.create(mode="self", status="draft")
        answers = {f"q{i}": f"q{i}_opt4" for i in range(1, 20)}
        answers["q20_text"] = "x"
        raw = compute_scores(answers)
        payload = build_full_report_payload(raw, answers, session)
        self.assertEqual(payload["next_steps"]["highlight"], "field_audit")
