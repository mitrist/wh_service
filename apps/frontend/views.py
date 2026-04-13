from __future__ import annotations

from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import AuditSession


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
