from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.calculations.bridge import build_answers_dict
from apps.calculations.score import QUESTION_BY_NUMBER, compute_scores
from apps.core.models import AnswerOption, AuditReport, AuditSession, Question, UserAnswer
from apps.reporting.report_builder import build_full_report_payload


@dataclass
class AnswerPatchInput:
    question_code: str
    option_id: Optional[str] = None
    open_answer_text: Optional[str] = None


def patch_session_answer(
    session: AuditSession,
    data: AnswerPatchInput,
) -> UserAnswer:
    if session.status != "draft":
        raise ValueError("Сессия не в статусе черновика.")

    try:
        question = Question.objects.get(code=data.question_code)
    except Question.DoesNotExist as exc:
        raise ValueError("Неизвестный question_code.") from exc

    if question.number == 20:
        text = (data.open_answer_text or "").strip()
        if not text and data.option_id:
            raise ValueError("Для q20 укажите open_answer_text.")
        ua, _ = UserAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                "open_answer_text": text,
                "selected_option": None,
            },
        )
        return ua

    if not data.option_id:
        raise ValueError("Укажите option_id (код варианта).")
    try:
        opt = AnswerOption.objects.get(question=question, code=data.option_id)
    except AnswerOption.DoesNotExist as exc:
        raise ValueError("Неизвестный option_id для этого вопроса.") from exc

    ua, _ = UserAnswer.objects.update_or_create(
        session=session,
        question=question,
        defaults={
            "selected_option": opt,
            "open_answer_text": "",
        },
    )
    return ua


def _enrich_top_problems(
    raw: Dict[str, Any],
    answers: Dict[str, Any],
) -> list[Dict[str, Any]]:
    out = []
    for g in raw.get("top_gaps", []):
        n = g["question_number"]
        opt_id = answers.get(f"q{n}")
        ball = 0
        if opt_id:
            q = QUESTION_BY_NUMBER[n]
            ball = q.get_option(opt_id).ball_percent
        out.append(
            {
                "question_code": f"q{n}",
                "question_text": g["title"],
                "score_percent": ball,
                "weight": QUESTION_BY_NUMBER[n].weight,
                "risk_score": g.get("risk_score"),
                "problem": g.get("problem", g["title"]),
                "impact": g.get("impact"),
                "quick_fix": g.get("quick_fix"),
                "limitation": g.get("limitation"),
            },
        )
    return out


# Ключи из logic.md cta_logic — в API отдаём готовую фразу для UI
CTA_FOCUS_BY_ZONE = {
    "green": "Зона в норме — дальше точечная оптимизация.",
    "yellow": "Системные риски — разберитесь в причинах.",
    "red": "Критично — важно остановить потери.",
}


def to_api_result_payload(raw: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
    zone = raw["overall_zone"]
    full_report = raw.get("full_report") or {}
    return {
        "total_score": float(raw["overall_index"]),
        "grade": zone,
        "cta_focus": CTA_FOCUS_BY_ZONE.get(zone, ""),
        "category_scores": {
            k: float(v["score_percent"]) for k, v in raw["criteria"].items()
        },
        "top_problems": _enrich_top_problems(raw, answers),
        "full_report": full_report,
    }


@transaction.atomic
def complete_session(session: AuditSession) -> Tuple[Dict[str, Any], AuditReport]:
    if session.mode != "self":
        raise ValueError("MVP: только режим self.")
    if session.status != "draft":
        raise ValueError("Сессия уже завершена или в архиве.")

    answers = build_answers_dict(session)
    try:
        raw = compute_scores(answers)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    raw["full_report"] = build_full_report_payload(raw, answers, session)

    q20 = (answers.get("q20_text") or "").strip()
    if not q20:
        raise ValueError("Заполните открытый ответ для вопроса 20.")

    email = (session.client_email or "").strip()
    if not email:
        raise ValueError("Укажите email и контактные данные перед завершением.")
    try:
        validate_email(email)
    except ValidationError as exc:
        raise ValueError("Некорректный email.") from exc

    api_result = to_api_result_payload(raw, answers)
    summary = {
        "engine": raw,
        "api": api_result,
        "client": {
            "name": session.client_name,
            "company": session.client_company,
            "email": session.client_email,
        },
    }

    session.total_score = float(raw["overall_index"])
    session.total_grade = raw["overall_zone"]
    session.status = "completed"
    session.completed_at = timezone.now()
    session.save(
        update_fields=[
            "total_score",
            "total_grade",
            "status",
            "completed_at",
            "last_modified",
        ],
    )

    report, _ = AuditReport.objects.update_or_create(
        session=session,
        defaults={"summary": summary},
    )
    return api_result, report
