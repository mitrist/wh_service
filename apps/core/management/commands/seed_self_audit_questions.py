from django.core.management.base import BaseCommand
from django.db import transaction

from apps.calculations.score import AUDIT_QUESTIONS
from apps.core.models import AnswerOption, Question


def _flow_order(question_number: int) -> int:
    """Порядок на экране: q1–q8, затем условный q21, затем q9–q20."""
    if question_number == 21:
        return 85
    if question_number <= 8:
        return question_number * 10
    return 90 + (question_number - 9) * 10


class Command(BaseCommand):
    help = "Seed self-audit questions and options from calculations.score.AUDIT_QUESTIONS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing self-audit rows (q1–q20) and re-insert",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options["force"]
        if force:
            Question.objects.filter(code__startswith="q").filter(number__lte=21).delete()

        created_q = 0
        created_o = 0
        for aq in AUDIT_QUESTIONS:
            q, q_created = Question.objects.update_or_create(
                code=f"q{aq.number}",
                defaults={
                    "number": aq.number,
                    "text": aq.title,
                    "category": aq.criterion or "",
                    "weight": aq.weight,
                    "order": _flow_order(aq.number),
                    "is_active": True,
                    "is_self_audit": True,
                    "hint": "",
                    "check_note": aq.check_note,
                    "impact_text": aq.impact_text or "",
                    "self_recommendation": "",
                    "pro_recommendation": "",
                },
            )
            if q_created:
                created_q += 1
            if not aq.options:
                continue
            for idx, opt in enumerate(aq.options, start=1):
                _, o_created = AnswerOption.objects.update_or_create(
                    question=q,
                    code=opt.option_id,
                    defaults={
                        "text": opt.label,
                        "score_percent": opt.ball_percent,
                        "after_answer_comment": opt.after_answer_comment or "",
                        "order": idx,
                    },
                )
                if o_created:
                    created_o += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Questions upserted; new questions: {created_q}, new options (approx): {created_o}",
            ),
        )
