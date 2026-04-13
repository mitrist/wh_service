from django.test import SimpleTestCase

from apps.reporting.pdf_generator import build_audit_pdf_bytes


class PdfGeneratorTests(SimpleTestCase):
    def test_build_pdf_from_full_report(self):
        session_meta = {"id": "sid", "company": "ACME", "email": "a@b.c"}
        summary = {
            "full_report": {
                "header": {
                    "company": "ACME",
                    "date": "01.01.2026",
                    "method": "Методика",
                    "disclaimer": ["Дисклеймер 1"],
                },
                "overall_index": {
                    "score_percent": 55,
                    "zone_label": "🟠 Системные проблемы",
                    "description": "desc",
                    "formula_note": "formula",
                },
                "criteria": {"rows": [{"emoji": "🎯", "title": "Точность", "score_percent": 50, "measured": "x"}]},
                "top_loss_points": [{"rank": 1, "title": "Проблема", "selected_answer": "Ответ", "market_norm": "Норма", "quick_solution": "fix"}],
                "market_benchmarks": {"rows": [{"title": "Ошибки", "your_result": "🔴", "good": "<0,1%"}]},
                "quick_wins": {"from_q20": "x", "personal_recommendation": "p", "yellow_zone_tip": "y", "universal_tip": "u"},
            },
        }
        pdf = build_audit_pdf_bytes(session_meta, summary)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)
