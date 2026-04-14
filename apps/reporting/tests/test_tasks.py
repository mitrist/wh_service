from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from apps.core.models import AuditReport, AuditSession
from apps.reporting.tasks import generate_pdf_report


class ReportingTasksTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="site@example.com",
    )
    @patch("apps.reporting.tasks.build_audit_pdf_bytes", return_value=b"%PDF-1.7 mock")
    def test_generate_pdf_report_sends_pdf_to_client_once(self, _mock_pdf_builder):
        session = AuditSession.objects.create(
            mode="self",
            status="completed",
            client_email="client@example.com",
            client_name="Client",
            client_company="ACME",
        )
        report = AuditReport.objects.create(session=session, summary={})

        result = generate_pdf_report(str(session.id))
        report.refresh_from_db()

        self.assertIn(f"session_{session.id}", result)
        self.assertTrue(report.pdf_file)
        self.assertIsNotNone(report.email_sent_at)
        self.assertEqual(report.email_error, "")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["client@example.com"])
        self.assertEqual(len(mail.outbox[0].attachments), 1)

        generate_pdf_report(str(session.id))
        self.assertEqual(len(mail.outbox), 1)

