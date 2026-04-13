from __future__ import annotations

import logging
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.core.models import AuditReport, AuditSession
from apps.reporting.pdf_generator import build_audit_pdf_bytes

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_pdf_report(self, session_id: str) -> str:
    try:
        session = AuditSession.objects.get(pk=session_id)
    except AuditSession.DoesNotExist:
        logger.warning("generate_pdf_report: session %s not found", session_id)
        return "missing"

    try:
        report = session.report
    except AuditReport.DoesNotExist:
        logger.warning("generate_pdf_report: no report for %s", session_id)
        return "no_report"

    summary = report.summary or {}
    pdf_bytes = build_audit_pdf_bytes(
        {
            "id": str(session.id),
            "company": session.client_company,
            "email": session.client_email,
            "name": session.client_name,
        },
        summary,
    )
    name = f"report_{session.id}_{int(timezone.now().timestamp())}.pdf"
    report.pdf_file.save(name, ContentFile(pdf_bytes), save=True)
    return str(report.pdf_file.name)
