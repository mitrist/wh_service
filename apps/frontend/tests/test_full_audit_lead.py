from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import FullAuditLead, NotificationLog


class FullAuditLeadSubmitTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FULL_AUDIT_NOTIFY_EMAILS=["notify@example.com"],
        DEFAULT_FROM_EMAIL="site@example.com",
        CELERY_TASK_ALWAYS_EAGER=True,
        NOTIFICATIONS_ENABLED=True,
    )
    def test_post_saves_lead_and_sends_email(self):
        url = reverse("frontend_full_audit_lead_submit")
        body = '{"name":"Иван","contact":"ivan@example.com","preferred_method":"email"}'
        r = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True})
        self.assertEqual(FullAuditLead.objects.count(), 1)
        lead = FullAuditLead.objects.get()
        self.assertEqual(lead.name, "Иван")
        self.assertTrue(lead.email_sent)
        self.assertEqual(lead.email_error, "")
        self.assertEqual(NotificationLog.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Иван", mail.outbox[0].subject)
        self.assertIn("ivan@example.com", mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FULL_AUDIT_NOTIFY_EMAILS=[],
        CELERY_TASK_ALWAYS_EAGER=True,
        NOTIFICATIONS_ENABLED=True,
    )
    def test_post_saves_without_mail_when_no_recipients(self):
        url = reverse("frontend_full_audit_lead_submit")
        body = '{"name":"A","contact":"b","preferred_method":"phone"}'
        r = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(FullAuditLead.objects.get().email_sent)
        self.assertEqual(NotificationLog.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_rejects_non_json(self):
        url = reverse("frontend_full_audit_lead_submit")
        r = self.client.post(url, data={"name": "x"}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 415)

    def test_post_validates_method(self):
        url = reverse("frontend_full_audit_lead_submit")
        body = '{"name":"A","contact":"b","preferred_method":"fax"}'
        r = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(r.status_code, 400)
