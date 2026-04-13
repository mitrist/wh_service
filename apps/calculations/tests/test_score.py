from django.test import SimpleTestCase

from apps.calculations.score import compute_scores, score_to_zone


class ScoreTests(SimpleTestCase):
    def test_score_to_zone_boundaries(self):
        self.assertEqual(score_to_zone(49), "red")
        self.assertEqual(score_to_zone(50), "yellow")
        self.assertEqual(score_to_zone(79), "yellow")
        self.assertEqual(score_to_zone(80), "green")

    def test_all_best_answers_high_score(self):
        answers = {f"q{i}": f"q{i}_opt1" for i in range(1, 20)}
        answers["q20_text"] = "Тест"
        r = compute_scores(answers)
        self.assertGreaterEqual(r["overall_index"], 80)
        self.assertEqual(r["overall_zone"], "green")

    def test_missing_answer_raises(self):
        answers = {f"q{i}": f"q{i}_opt1" for i in range(1, 19)}
        answers["q20_text"] = ""
        with self.assertRaises(ValueError):
            compute_scores(answers)

    def test_top_gaps_by_highest_risk(self):
        # Все худшие варианты: risk = 100 * weight; среди веса 3 первыми идут q2, q4, q5.
        answers = {f"q{i}": f"q{i}_opt4" for i in range(1, 20)}
        answers["q20_text"] = "x"
        r = compute_scores(answers)
        self.assertEqual(len(r["top_gaps"]), 3)
        nums = [g["question_number"] for g in r["top_gaps"]]
        self.assertEqual(nums, [2, 4, 5])
        for g in r["top_gaps"]:
            self.assertIn("risk_score", g)
            self.assertIn("limitation", g)
            self.assertEqual(g["risk_score"], 300)
