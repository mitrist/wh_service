from django.core import mail
from django.test import TestCase, override_settings

from apps.core.models import NotificationLog
from apps.notifications.events import NotificationEvent
from apps.notifications.services import (
    RECIPIENT_GROUP_INTERNAL,
    enqueue_form_notification,
    resolve_recipients,
)


class NotificationServiceTests(TestCase):
    @override_settings(
        FORM_NOTIFY_DEFAULT_EMAILS=["default@example.com"],
        FORM_NOTIFY_SELF_AUDIT_EMAILS=[],
    )
    def test_resolve_recipients_fallback_to_default(self):
        recipients = resolve_recipients(
            event_type=NotificationEvent.SELF_AUDIT_COMPLETED,
            recipient_group=RECIPIENT_GROUP_INTERNAL,
        )
        self.assertEqual(recipients, ["default@example.com"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="site@example.com",
        CELERY_TASK_ALWAYS_EAGER=True,
        NOTIFICATIONS_ENABLED=True,
        FORM_NOTIFY_DEFAULT_EMAILS=[],
        FORM_NOTIFY_SELF_AUDIT_EMAILS=["ops@example.com"],
    )
    def test_enqueue_creates_log_and_sends_mail(self):
        log = enqueue_form_notification(
            event_type=NotificationEvent.SELF_AUDIT_CONTACT_CAPTURED,
            entity_id="session-1",
            payload={
                "session_id": "session-1",
                "email": "client@example.com",
                "name": "Client",
                "company": "Acme",
            },
            context={"source": "test"},
        )
        self.assertIsNotNone(log)
        self.assertEqual(NotificationLog.objects.count(), 1)
        saved = NotificationLog.objects.get()
        self.assertEqual(saved.status, NotificationLog.STATUS_SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("client@example.com", mail.outbox[0].subject)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="site@example.com",
        CELERY_TASK_ALWAYS_EAGER=True,
        NOTIFICATIONS_ENABLED=True,
        FORM_NOTIFY_DEFAULT_EMAILS=[],
        FORM_NOTIFY_SELF_AUDIT_EMAILS=["ops@example.com"],
    )
    def test_dedup_by_event_entity_and_group(self):
        first = enqueue_form_notification(
            event_type=NotificationEvent.SELF_AUDIT_COMPLETED,
            entity_id="session-2",
            payload={"session_id": "session-2", "email": "a@example.com"},
            context={},
        )
        second = enqueue_form_notification(
            event_type=NotificationEvent.SELF_AUDIT_COMPLETED,
            entity_id="session-2",
            payload={"session_id": "session-2", "email": "a@example.com"},
            context={},
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, second.id)
        self.assertEqual(NotificationLog.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
