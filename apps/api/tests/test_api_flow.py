from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import NotificationLog, Question


class ApiFlowTests(TestCase):
    fixtures = []

    @classmethod
    def setUpTestData(cls):
        if Question.objects.count() == 0:
            from django.core.management import call_command

            call_command("seed_self_audit_questions")

    def setUp(self):
        self.client = APIClient()

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CELERY_TASK_ALWAYS_EAGER=True,
        NOTIFICATIONS_ENABLED=True,
        FORM_NOTIFY_SELF_AUDIT_EMAILS=["ops@example.com"],
    )
    def test_create_patch_complete_and_report(self):
        r = self.client.post("/api/v1/sessions/", {"mode": "self"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        sid = r.json()["id"]
        for i in range(1, 20):
            pr = self.client.patch(
                f"/api/v1/sessions/{sid}/answers/",
                {"question_code": f"q{i}", "option_id": f"q{i}_opt1"},
                format="json",
            )
            self.assertEqual(pr.status_code, 200, pr.content)
        pr = self.client.patch(
            f"/api/v1/sessions/{sid}/answers/",
            {"question_code": "q20", "open_answer_text": "Навигация"},
            format="json",
        )
        self.assertEqual(pr.status_code, 200, pr.content)
        up = self.client.patch(
            f"/api/v1/sessions/{sid}/",
            {
                "client_email": "t@example.com",
                "client_name": "T",
                "client_company": "C",
            },
            format="json",
        )
        self.assertEqual(up.status_code, 200, up.content)
        cr = self.client.post(f"/api/v1/sessions/{sid}/complete/", format="json")
        self.assertEqual(cr.status_code, 200, cr.content)
        event_types = set(
            NotificationLog.objects.filter(entity_id=sid).values_list("event_type", flat=True),
        )
        self.assertIn("self_audit_contact_captured", event_types)
        self.assertIn("self_audit_completed", event_types)
        body = cr.json()
        self.assertIn("result", body)
        self.assertIn("cta_focus", body["result"])
        self.assertTrue(body["result"]["top_problems"][0].get("risk_score") is not None)
        self.assertIn("full_report", body["result"])
        self.assertIn("overall_index", body["result"]["full_report"])
        self.assertIn("top_loss_points", body["result"]["full_report"])
        rep = self.client.get(f"/api/v1/sessions/{sid}/report/")
        self.assertIn(rep.status_code, (200, 202))
        if rep.status_code == 200:
            self.assertEqual(rep["Content-Type"], "application/pdf")

    def test_complete_requires_email(self):
        r = self.client.post("/api/v1/sessions/", {"mode": "self"}, format="json")
        sid = r.json()["id"]
        for i in range(1, 20):
            self.client.patch(
                f"/api/v1/sessions/{sid}/answers/",
                {"question_code": f"q{i}", "option_id": f"q{i}_opt1"},
                format="json",
            )
        self.client.patch(
            f"/api/v1/sessions/{sid}/answers/",
            {"question_code": "q20", "open_answer_text": "x"},
            format="json",
        )
        cr = self.client.post(f"/api/v1/sessions/{sid}/complete/", format="json")
        self.assertEqual(cr.status_code, 400)
