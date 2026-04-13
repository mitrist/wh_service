from __future__ import annotations

from django.test import SimpleTestCase

from health.audit_engine import compute_scores


class HealthAuditEngineTests(SimpleTestCase):
    def test_compute_scores_best_case(self):
        answers = {f"q{i}": f"q{i}_opt1" for i in range(1, 20)}
        answers["q20_text"] = "любое"

        result = compute_scores(answers)

        self.assertEqual(result["overall_index"], 100)
        self.assertEqual(result["overall_zone"], "green")
        for crit in ("accuracy", "speed", "capacity", "manageability"):
            self.assertEqual(result["criteria"][crit]["score_percent"], 100)
            self.assertEqual(result["criteria"][crit]["zone"], "green")

    def test_compute_scores_worst_case(self):
        # opt4 has 0% ball for all weight-3/weight-2 questions except Q8/Q12/Q17 where opt4 is also 0%.
        answers = {f"q{i}": f"q{i}_opt4" for i in range(1, 20)}
        answers["q20_text"] = "любое"

        result = compute_scores(answers)

        self.assertEqual(result["overall_index"], 0)
        self.assertEqual(result["overall_zone"], "red")
        for crit in ("accuracy", "speed", "capacity", "manageability"):
            self.assertEqual(result["criteria"][crit]["score_percent"], 0)
            self.assertEqual(result["criteria"][crit]["zone"], "red")

    def test_top_gaps_picks_three_worst_weight3(self):
        answers = {f"q{i}": f"q{i}_opt1" for i in range(1, 20)}
        answers["q20_text"] = "Сделать нормальную навигацию"

        # Weight=3 questions: 2, 4, 5, 14, 17
        # Set their ball percents to produce deterministic ordering:
        # q2 -> 0, q4 -> 33, q14 -> 33, q5 -> 67, q17 -> 80
        answers["q2"] = "q2_opt4"  # 0
        answers["q4"] = "q4_opt3"  # 33
        answers["q5"] = "q5_opt2"  # 67
        answers["q14"] = "q14_opt3"  # 33
        answers["q17"] = "q17_opt2"  # 80

        result = compute_scores(answers)
        top = result["top_gaps"]
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0]["question_number"], 2)
        self.assertEqual(top[1]["question_number"], 4)
        self.assertEqual(top[2]["question_number"], 14)
