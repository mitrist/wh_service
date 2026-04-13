from __future__ import annotations

import json
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import AuditSession, FullAuditLead

logger = logging.getLogger(__name__)

_MAX_FULL_AUDIT_NAME = 200
_MAX_FULL_AUDIT_CONTACT = 500


def home(request):
    return render(
        request,
        "frontend/home.html",
        {
            "api_base": "/api/v1",
        },
    )


@require_POST
def audit_begin(request):
    session = AuditSession.objects.create(
        mode="self",
        status="draft",
        client_email="",
    )
    return redirect("frontend_self_audit_session", session_id=session.id)


def self_audit_session(request, session_id):
    return render(
        request,
        "frontend/self_audit_quiz.html",
        {
            "session_id": session_id,
            "api_base": "/api/v1",
        },
    )


def self_audit_contact(request, session_id):
    return render(
        request,
        "frontend/self_audit_contact.html",
        {
            "session_id": session_id,
            "api_base": "/api/v1",
        },
    )


def self_audit_result(request, session_id):
    return render(
        request,
        "frontend/self_audit_result.html",
        {
            "session_id": session_id,
            "api_base": "/api/v1",
        },
    )


@require_POST
def full_audit_lead_submit(request):
    """Приём заявки «Заказать полный аудит»: БД + опционально письмо на FULL_AUDIT_NOTIFY_EMAILS."""
    ctype = (request.content_type or "").split(";")[0].strip().lower()
    if ctype != "application/json":
        return JsonResponse({"ok": False, "error": "json_required"}, status=415)
    try:
        payload = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    name = str(payload.get("name", "")).strip()
    contact = str(payload.get("contact", "")).strip()
    preferred_method = str(payload.get("preferred_method", "")).strip()
    if not name or not contact or not preferred_method:
        return JsonResponse({"ok": False, "error": "required_fields"}, status=400)
    if preferred_method not in (FullAuditLead.METHOD_EMAIL, FullAuditLead.METHOD_PHONE):
        return JsonResponse({"ok": False, "error": "invalid_method"}, status=400)
    if len(name) > _MAX_FULL_AUDIT_NAME or len(contact) > _MAX_FULL_AUDIT_CONTACT:
        return JsonResponse({"ok": False, "error": "too_long"}, status=400)

    lead = FullAuditLead.objects.create(
        name=name,
        contact=contact,
        preferred_method=preferred_method,
    )

    recipients = [e.strip() for e in settings.FULL_AUDIT_NOTIFY_EMAILS if e and str(e).strip()]
    if recipients:
        method_label = dict(FullAuditLead.PREFERRED_METHOD_CHOICES).get(
            preferred_method,
            preferred_method,
        )
        subject = f"Заявка на полный аудит: {name}"
        body = (
            f"Имя: {name}\n"
            f"Контакт: {contact}\n"
            f"Предпочитаемый способ связи: {method_label}\n"
        )
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
            lead.email_sent = True
            lead.save(update_fields=["email_sent"])
        except Exception as exc:
            logger.exception("full_audit_lead: send_mail failed for lead id=%s", lead.id)
            lead.email_error = str(exc)[:1000]
            lead.save(update_fields=["email_error"])

    return JsonResponse({"ok": True})
