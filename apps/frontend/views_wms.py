from __future__ import annotations

import io
import json
from typing import Dict
from uuid import UUID

from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import WmsChecklistAnswer, WmsChecklistSession
from apps.frontend.wms_checklist_data import (
    ITEM_BY_NUMBER,
    WMS_CHECKLIST_ITEMS,
    count_ready_answers,
    resolve_wms_band,
)
from apps.notifications.events import NotificationEvent
from apps.notifications.services import enqueue_form_notification
from apps.reporting.pdf_generator import build_wms_checklist_pdf_bytes


def _answers_map(session: WmsChecklistSession) -> Dict[int, str | None]:
    out: Dict[int, str | None] = {i: None for i in range(1, 11)}
    for a in session.answers.all():
        if 1 <= a.item_number <= 10:
            out[a.item_number] = a.status
    return out


def _filled_count(status_by_item: Dict[int, str | None]) -> int:
    return sum(1 for n in range(1, 11) if status_by_item.get(n) not in (None, ""))


def _all_answered(status_by_item: Dict[int, str | None]) -> bool:
    return _filled_count(status_by_item) == 10


@require_GET
def wms_checklist_landing(request):
    return render(
        request,
        "frontend/wms_checklist_landing.html",
        {
            "api_base": "/api/v1",
        },
    )


@require_POST
def wms_checklist_begin(request):
    session = WmsChecklistSession.objects.create()
    WmsChecklistAnswer.objects.bulk_create(
        [
            WmsChecklistAnswer(session=session, item_number=n, status=None)
            for n in range(1, 11)
        ],
    )
    return redirect("frontend_wms_checklist_session", session_id=session.id)


@require_GET
def wms_checklist_pdf_template(request):
    pdf = build_wms_checklist_pdf_bytes(session_id=None, status_by_item={})
    return FileResponse(
        io.BytesIO(pdf),
        as_attachment=True,
        filename="checklist-wms-gotovnost.pdf",
        content_type="application/pdf",
    )


@require_GET
def wms_checklist_session(request, session_id: UUID):
    session = get_object_or_404(WmsChecklistSession.objects.prefetch_related("answers"), id=session_id)
    status_by_item = _answers_map(session)
    score = count_ready_answers(status_by_item)
    band = resolve_wms_band(score) if _all_answered(status_by_item) else None
    not_ready_titles = [
        ITEM_BY_NUMBER[n].title
        for n in range(1, 11)
        if status_by_item.get(n) == WmsChecklistAnswer.STATUS_NOT_READY
    ]
    in_progress_titles = [
        ITEM_BY_NUMBER[n].title
        for n in range(1, 11)
        if status_by_item.get(n) == WmsChecklistAnswer.STATUS_IN_PROGRESS
    ]
    items_rows = [{"item": it, "status": status_by_item.get(it.number)} for it in WMS_CHECKLIST_ITEMS]

    return render(
        request,
        "frontend/wms_checklist_session.html",
        {
            "session_id": session_id,
            "items_rows": items_rows,
            "filled_count": _filled_count(status_by_item),
            "all_answered": _all_answered(status_by_item),
            "score": score,
            "band": band,
            "not_ready_titles": not_ready_titles,
            "in_progress_titles": in_progress_titles,
        },
    )


@require_POST
def wms_checklist_answer(request, session_id: UUID):
    session = get_object_or_404(WmsChecklistSession, id=session_id)
    ctype = (request.content_type or "").split(";")[0].strip().lower()
    if ctype != "application/json":
        return JsonResponse({"ok": False, "error": "json_required"}, status=415)
    try:
        payload = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    try:
        item_number = int(payload.get("item_number"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "bad_item"}, status=400)
    if item_number < 1 or item_number > 10:
        return JsonResponse({"ok": False, "error": "bad_item"}, status=400)

    status = payload.get("status")
    if status is not None and status not in (
        WmsChecklistAnswer.STATUS_READY,
        WmsChecklistAnswer.STATUS_IN_PROGRESS,
        WmsChecklistAnswer.STATUS_NOT_READY,
    ):
        return JsonResponse({"ok": False, "error": "bad_status"}, status=400)

    WmsChecklistAnswer.objects.filter(session=session, item_number=item_number).update(status=status)
    WmsChecklistSession.objects.filter(pk=session.pk).update(updated_at=timezone.now())

    status_by_item = _answers_map(
        WmsChecklistSession.objects.prefetch_related("answers").get(pk=session.pk),
    )
    filled = _filled_count(status_by_item)
    all_ok = _all_answered(status_by_item)
    score = count_ready_answers(status_by_item)
    band = resolve_wms_band(score) if all_ok else None

    not_ready_titles = [
        ITEM_BY_NUMBER[n].title
        for n in range(1, 11)
        if status_by_item.get(n) == WmsChecklistAnswer.STATUS_NOT_READY
    ]
    in_progress_titles = [
        ITEM_BY_NUMBER[n].title
        for n in range(1, 11)
        if status_by_item.get(n) == WmsChecklistAnswer.STATUS_IN_PROGRESS
    ]
    if all_ok and band:
        enqueue_form_notification(
            event_type=NotificationEvent.WMS_CHECKLIST_COMPLETED,
            entity_id=str(session.id),
            payload={
                "session_id": str(session.id),
                "score": score,
                "band_title": band.get("title", ""),
                "not_ready_count": len(not_ready_titles),
                "in_progress_count": len(in_progress_titles),
            },
            context={"source": "wms_checklist"},
        )

    return JsonResponse(
        {
            "ok": True,
            "filled_count": filled,
            "all_answered": all_ok,
            "score": score,
            "band": band,
            "not_ready_titles": not_ready_titles,
            "in_progress_titles": in_progress_titles,
        },
    )


@require_GET
def wms_checklist_pdf_session(request, session_id: UUID):
    session = get_object_or_404(WmsChecklistSession.objects.prefetch_related("answers"), id=session_id)
    status_by_item = _answers_map(session)
    pdf = build_wms_checklist_pdf_bytes(session_id=str(session_id), status_by_item=status_by_item)
    return FileResponse(
        io.BytesIO(pdf),
        as_attachment=True,
        filename=f"checklist-wms-{session_id}.pdf",
        content_type="application/pdf",
    )
