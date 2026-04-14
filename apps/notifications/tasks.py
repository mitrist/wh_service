from __future__ import annotations

import logging
from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.models import NotificationLog
from apps.notifications.events import NotificationEvent

logger = logging.getLogger(__name__)

_SUBJECT_BY_EVENT = {
    NotificationEvent.FULL_AUDIT_LEAD_CREATED: "Заявка на полный аудит: {name}",
    NotificationEvent.SELF_AUDIT_CONTACT_CAPTURED: "Self-audit: получен контакт {email}",
    NotificationEvent.SELF_AUDIT_COMPLETED: "Self-audit завершен: {email}",
    NotificationEvent.WMS_CHECKLIST_COMPLETED: "WMS checklist завершен: сессия {session_id}",
}

_TEMPLATE_BY_EVENT = {
    NotificationEvent.FULL_AUDIT_LEAD_CREATED: "notifications/email/full_audit_lead_created.txt",
    NotificationEvent.SELF_AUDIT_CONTACT_CAPTURED: "notifications/email/self_audit_contact_captured.txt",
    NotificationEvent.SELF_AUDIT_COMPLETED: "notifications/email/self_audit_completed.txt",
    NotificationEvent.WMS_CHECKLIST_COMPLETED: "notifications/email/wms_checklist_completed.txt",
}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_form_notification(self, log_id: int) -> str:
    try:
        log = NotificationLog.objects.get(pk=log_id)
    except NotificationLog.DoesNotExist:
        logger.warning("send_form_notification: log %s not found", log_id)
        return "missing"

    if log.status == NotificationLog.STATUS_SENT:
        return "already_sent"

    recipients = [e.strip() for e in (log.recipients or []) if e and str(e).strip()]
    if not recipients:
        log.status = NotificationLog.STATUS_SKIPPED
        log.error = "Recipients are empty"
        log.attempts += 1
        log.save(update_fields=["status", "error", "attempts"])
        return "skipped"

    event_type = log.event_type
    payload = log.payload or {}
    context = log.context or {}
    template_name = _TEMPLATE_BY_EVENT.get(event_type)
    if not template_name:
        log.status = NotificationLog.STATUS_FAILED
        log.error = f"Unknown event_type: {event_type}"
        log.attempts += 1
        log.save(update_fields=["status", "error", "attempts"])
        return "failed"

    format_payload = {k: v for k, v in payload.items() if isinstance(v, (str, int, float))}
    subject_template = _SUBJECT_BY_EVENT.get(event_type, "Новая заявка с сайта")
    subject = subject_template.format(**format_payload)
    body = render_to_string(
        template_name,
        {
            "event_type": event_type,
            "payload": payload,
            "context": context,
            "log": log,
        },
    ).strip()

    log.attempts += 1
    try:
        sent_count = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        if sent_count:
            log.status = NotificationLog.STATUS_SENT
            log.sent_at = timezone.now()
            log.error = ""
        else:
            log.status = NotificationLog.STATUS_FAILED
            log.error = "send_mail returned 0"
        log.message_id = f"sent:{sent_count}"
        log.save(update_fields=["status", "sent_at", "error", "attempts", "message_id"])
        return "sent"
    except SMTPException as exc:
        log.status = NotificationLog.STATUS_FAILED
        log.error = str(exc)[:1000]
        log.save(update_fields=["status", "error", "attempts"])
        raise self.retry(exc=exc)
    except Exception as exc:
        log.status = NotificationLog.STATUS_FAILED
        log.error = str(exc)[:1000]
        log.save(update_fields=["status", "error", "attempts"])
        logger.exception("send_form_notification failed for log id=%s", log_id)
        return "failed"
