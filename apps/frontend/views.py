from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.models import AuditSession, FullAuditLead

logger = logging.getLogger(__name__)

_MAX_FULL_AUDIT_NAME = 200
_MAX_FULL_AUDIT_CONTACT = 500
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WP_SOLUTIONS = [
    {
        "slug": "proizvodstvo",
        "title": "Производство",
        "short": "Контроль всех этапов работы склада, от маркировки товаров до учета их движения.",
        "description": "Поддержка адресного хранения, сокращение простоев линии и прозрачный контроль комплектования в производственной логистике.",
    },
    {
        "slug": "alcogol",
        "title": "Алкоголь",
        "short": "Контроль соблюдения правил хранения и транспортировки алкогольной продукции.",
        "description": "Учет партий и сроков, прослеживаемость и дисциплина складских операций для регламентированной алкогольной продукции.",
    },
    {
        "slug": "oborudovanie",
        "title": "Оборудование",
        "short": "Учет и управление движением оборудования на складе.",
        "description": "Контроль единиц оборудования, статусов и перемещений между зонами хранения и отгрузки.",
    },
    {
        "slug": "odezda-i-obuv",
        "title": "Одежда и обувь",
        "short": "Автоматизация учета и обработки размерных сеток, сезонности модельного ряда и других специфических процессов.",
        "description": "Поддержка размерных матриц, сезонных коллекций и ускоренная комплектация для омниканальных продаж.",
    },
    {
        "slug": "retail",
        "title": "Ритейл",
        "short": "Упрощение и оптимизация процессов управления складом и товарным запасом.",
        "description": "Повышение оборачиваемости, снижение ошибок сборки и быстрая обработка поставок для розничных операций.",
    },
    {
        "slug": "farmacevtika",
        "title": "Фармацевтика",
        "short": "Точный учет продукции, включая отслеживание сроков годности, партий и серий товара.",
        "description": "Серийный учет, FIFO/FEFO и контроль сроков годности для соответствия отраслевым требованиям.",
    },
]
_WP_SOLUTIONS_BY_SLUG = {item["slug"]: item for item in _WP_SOLUTIONS}
_WP_SERVICES_META = [
    {"slug": "log_audit", "title": "Логистический аудит склада", "file": "log_audit.md"},
    {"slug": "avtomatizacziya-skladov-i-wms", "title": "Автоматизация складов и WMS", "file": "avtomatizacziya-skladov-i-wms.md"},
    {
        "slug": "tehnicheskoe-soprovozhdenie-i-podderzhka-po",
        "title": "Техническое сопровождение и поддержка 1С:WMS Логистика. Управление складом",
        "file": "tehnicheskoe-soprovozhdenie-i-podderzhka-po.md",
    },
    {"slug": "konsultacziya-ot-ekspertov", "title": "Консультация от экспертов", "file": "konsultacziya-ot-ekspertov.md"},
    {"slug": "skladskaya-analitika", "title": "Складская аналитика", "file": "skladskaya-analitika.md"},
]


def _load_service_content(file_name: str) -> dict[str, object]:
    path = _PROJECT_ROOT / ".cursor" / "uslugi" / file_name
    raw = path.read_text(encoding="utf-8").strip()
    lines = [line.strip() for line in raw.splitlines()]
    non_empty = [line for line in lines if line]
    title = non_empty[0] if non_empty else file_name
    body_lines = non_empty[1:] if len(non_empty) > 1 else []
    return {"title": title, "body_lines": body_lines, "source_file": file_name}


def _get_wp_services() -> list[dict[str, object]]:
    services = []
    for item in _WP_SERVICES_META:
        content = _load_service_content(item["file"])
        services.append(
            {
                "slug": item["slug"],
                "title": item["title"],
                "body_lines": content["body_lines"],
                "source_file": content["source_file"],
            }
        )
    return services


def home(request):
    services = _get_wp_services()
    return render(
        request,
        "frontend/wp_home.html",
        {
            "api_base": "/api/v1",
            "solutions": _WP_SOLUTIONS,
            "services": services,
            "canonical_url": request.build_absolute_uri("/"),
        },
    )


def solutions(request):
    return render(
        request,
        "frontend/wp_solutions.html",
        {
            "solutions": _WP_SOLUTIONS,
            "canonical_url": request.build_absolute_uri("/solutions/"),
        },
    )


def solution_detail(request, slug: str):
    solution = _WP_SOLUTIONS_BY_SLUG.get(slug)
    if not solution:
        raise Http404("Solution not found")
    return render(
        request,
        "frontend/wp_solution_detail.html",
        {
            "solution": solution,
            "solutions": _WP_SOLUTIONS,
            "canonical_url": request.build_absolute_uri(f"/solutions/{slug}"),
        },
    )


def service_detail(request, slug: str):
    services_by_slug = {item["slug"]: item for item in _get_wp_services()}
    service = services_by_slug.get(slug)
    if not service:
        raise Http404("Service not found")
    return render(
        request,
        "frontend/wp_service_detail.html",
        {
            "service": service,
            "canonical_url": request.build_absolute_uri(f"/services/{slug}/"),
        },
    )


def self_audit_landing(request):
    return render(
        request,
        "frontend/self_audit_landing.html",
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
