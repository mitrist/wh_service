from __future__ import annotations

from typing import Any

from django.conf import settings
from apps.core.models import NotificationLog
from apps.notifications.events import NotificationEvent
from apps.notifications.tasks import send_form_notification

RECIPIENT_GROUP_INTERNAL = "internal"
RECIPIENT_GROUP_CLIENT = "client"


def _clean_emails(emails: list[str] | tuple[str, ...]) -> list[str]:
    return [email.strip() for email in emails if email and str(email).strip()]


def resolve_recipients(event_type: str, recipient_group: str) -> list[str]:
    default_emails = _clean_emails(getattr(settings, "FORM_NOTIFY_DEFAULT_EMAILS", []))
    if recipient_group == RECIPIENT_GROUP_CLIENT:
        return []

    if event_type == NotificationEvent.FULL_AUDIT_LEAD_CREATED:
        event_emails = _clean_emails(getattr(settings, "FORM_NOTIFY_FULL_AUDIT_EMAILS", []))
        legacy_emails = _clean_emails(getattr(settings, "FULL_AUDIT_NOTIFY_EMAILS", []))
        return event_emails or legacy_emails or default_emails

    if event_type in (
        NotificationEvent.SELF_AUDIT_CONTACT_CAPTURED,
        NotificationEvent.SELF_AUDIT_COMPLETED,
    ):
        event_emails = _clean_emails(getattr(settings, "FORM_NOTIFY_SELF_AUDIT_EMAILS", []))
        return event_emails or default_emails

    if event_type == NotificationEvent.WMS_CHECKLIST_COMPLETED:
        event_emails = _clean_emails(getattr(settings, "FORM_NOTIFY_WMS_CHECKLIST_EMAILS", []))
        return event_emails or default_emails

    return default_emails


def enqueue_form_notification(
    *,
    event_type: str,
    entity_id: str,
    payload: dict[str, Any],
    context: dict[str, Any] | None = None,
    recipient_group: str = RECIPIENT_GROUP_INTERNAL,
) -> NotificationLog | None:
    if not getattr(settings, "NOTIFICATIONS_ENABLED", True):
        return None

    recipients = resolve_recipients(event_type=event_type, recipient_group=recipient_group)
    if not recipients and recipient_group == RECIPIENT_GROUP_INTERNAL:
        return None

    log, created = NotificationLog.objects.get_or_create(
        event_type=event_type,
        entity_id=str(entity_id),
        recipient_group=recipient_group,
        defaults={
            "recipients": recipients,
            "payload": payload or {},
            "context": context or {},
            "status": NotificationLog.STATUS_PENDING,
        },
    )
    if not created:
        return log

    send_form_notification.delay(log.id)
    return log
