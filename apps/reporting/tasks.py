from __future__ import annotations

import logging
from celery import shared_task
from django.core.mail import EmailMessage
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
    # Отправляем PDF клиенту один раз после успешной генерации.
    if session.client_email and not report.email_sent_at:
        subject = "Ваш PDF-отчёт по самоаудиту склада"
        body = (
            "Здравствуйте!\n\n"
            "Отправляем ваш PDF-отчёт по самоаудиту склада во вложении.\n"
            "Если у вас появятся вопросы по результатам, ответьте на это письмо.\n\n"
            "С уважением,\n"
            "Команда Райтек Логистика"
        )
        try:
            message = EmailMessage(
                subject=subject,
                body=body,
                to=[session.client_email],
            )
            message.attach(
                filename=f"audit_report_{session.id}.pdf",
                content=pdf_bytes,
                mimetype="application/pdf",
            )
            message.send(fail_silently=False)
            report.email_sent_at = timezone.now()
            report.email_error = ""
            report.save(update_fields=["email_sent_at", "email_error"])
        except Exception as exc:
            logger.exception("generate_pdf_report: report email send failed for %s", session_id)
            report.email_error = str(exc)[:1000]
            report.save(update_fields=["email_error"])
    return str(report.pdf_file.name)
