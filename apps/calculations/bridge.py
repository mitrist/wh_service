"""Build answer dict for compute_scores from ORM session."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from apps.core.models import AuditSession


def build_answers_dict(session: "AuditSession") -> Dict[str, Any]:
    """
    Maps UserAnswer rows to keys expected by apps.calculations.score.compute_scores:
    q1..q19 и опционально q21 -> AnswerOption.code; q20_text -> открытый ответ.
    """
    out: Dict[str, Any] = {}
    for ua in session.answers.select_related("question", "selected_option").order_by(
        "question__order",
    ):
        q = ua.question
        if q.number == 20:
            out["q20_text"] = (ua.open_answer_text or "").strip()
            continue
        if ua.selected_option_id and ua.selected_option:
            out[q.code] = ua.selected_option.code
    return out
