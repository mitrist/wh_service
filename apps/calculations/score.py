"""
Расчёт баллов и топ-проблем по правилам из logic.md в корне проекта:
взвешенное среднее, зоны 80/50, критерии speed/accuracy/capacity/manageability,
топ-3 по risk = (100 - ball) * weight, cta_logic по общей зоне.

Тексты вопросов и микро-комментарии — apps.calculations.audit_questions (quiz.md, comments.md).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from apps.calculations.audit_questions import (
    AUDIT_QUESTIONS,
    AuditOption,
    AuditQuestion,
    QUESTION_BY_NUMBER,
)

CRITICAL_THRESHOLDS: Tuple[int, int] = (49, 79)


def score_to_zone(score_percent: int) -> str:
    """
    Convert score to zone name (prototype colours).

    - 0..49 => "red"
    - 50..79 => "yellow"
    - 80..100 => "green"
    """
    if score_percent <= CRITICAL_THRESHOLDS[0]:
        return "red"
    if score_percent <= CRITICAL_THRESHOLDS[1]:
        return "yellow"
    return "green"


def _round_int(value: float) -> int:
    return int(value + 0.5)


# Текст ограничения для топ-проблем (logic.md output.include limitation)
TOP_PROBLEM_LIMITATION = (
    "Точных рублей по этой точке опросник не показывает — нужен выездной аудит."
)


def _score_weighted_average(
    items: List[Tuple[int, int]],
    *,
    default: int = 0,
) -> int:
    weight_sum = sum(w for _, w in items)
    if weight_sum <= 0:
        return default
    weighted = sum(ball * w for ball, w in items) / weight_sum
    return _round_int(weighted)


def compute_scores(answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    answers:
      - q1..q19: selected option_id strings (q21 опционален, не влияет на скоринг)
      - q20_text: free text (optional)
    """
    scored_questions = [q for q in AUDIT_QUESTIONS if q.is_scored()]

    selected_option_ids: Dict[int, str] = {}
    for q in scored_questions:
        key = f"q{q.number}"
        option_id = answers.get(key)
        if not option_id or not isinstance(option_id, str):
            raise ValueError(f"Missing required answer for {key}.")
        selected_option_ids[q.number] = option_id
        _ = q.get_option(option_id)

    total_items: List[Tuple[int, int]] = []
    for q in scored_questions:
        opt = q.get_option(selected_option_ids[q.number])
        total_items.append((opt.ball_percent, q.weight))

    total_score = _score_weighted_average(total_items, default=0)
    total_zone = score_to_zone(total_score)

    criteria_keys = ["accuracy", "speed", "capacity", "manageability"]
    criteria_scores: Dict[str, Dict[str, Any]] = {}
    for crit in criteria_keys:
        crit_items: List[Tuple[int, int]] = []
        for q in scored_questions:
            if q.criterion == crit:
                opt = q.get_option(selected_option_ids[q.number])
                crit_items.append((opt.ball_percent, q.weight))
        crit_score = _score_weighted_average(crit_items, default=0)
        criteria_scores[crit] = {
            "score_percent": crit_score,
            "zone": score_to_zone(crit_score),
        }

    risk_rows: List[Tuple[int, int, int]] = []
    for q in scored_questions:
        opt = q.get_option(selected_option_ids[q.number])
        ball = opt.ball_percent
        risk = (100 - ball) * q.weight
        risk_rows.append((risk, q.number, ball))
    risk_rows.sort(key=lambda t: (-t[0], t[1]))
    top3 = risk_rows[:3]

    top_gaps: List[Dict[str, Any]] = []
    for risk, q_number, _ball in top3:
        q = QUESTION_BY_NUMBER[q_number]
        opt = q.get_option(selected_option_ids[q_number])
        impact_line = (q.impact_text or "").strip() or f"Ваш ответ: {opt.label}"
        top_gaps.append(
            {
                "question_number": q_number,
                "title": q.title,
                "selected_label": opt.label,
                "selected_score_percent": opt.ball_percent,
                "check_note": q.check_note,
                "impact_text": q.impact_text,
                "risk_score": risk,
                "problem": q.title,
                "impact": impact_line,
                "quick_fix": q.check_note,
                "limitation": TOP_PROBLEM_LIMITATION,
            },
        )

    q20_text = answers.get("q20_text") or ""
    q20_text = str(q20_text).strip()

    return {
        "overall_index": total_score,
        "overall_zone": total_zone,
        "criteria": criteria_scores,
        "top_gaps": top_gaps,
        "quick_win_quote": q20_text,
    }


__all__ = [
    "AUDIT_QUESTIONS",
    "AuditOption",
    "AuditQuestion",
    "QUESTION_BY_NUMBER",
    "CRITICAL_THRESHOLDS",
    "TOP_PROBLEM_LIMITATION",
    "compute_scores",
    "score_to_zone",
]
