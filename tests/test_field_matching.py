import unittest

from jobsearch.apply.field_matching import MIN_FILL_CONFIDENCE, score_field


class TestScoreField(unittest.TestCase):
    def test_strong_attribute_match_clears_threshold(self):
        attrs = {"name": "candidate_email", "placeholder": ""}
        score = score_field(attrs, ["email"])
        self.assertGreaterEqual(score, MIN_FILL_CONFIDENCE)

    def test_weak_only_match_stays_below_threshold(self):
        # A hint that only appears in placeholder/text must not be enough to fill.
        attrs = {"name": "field_1", "id": "f1", "label": "", "placeholder": "Enter your email"}
        score = score_field(attrs, ["email"])
        self.assertEqual(score, 1)
        self.assertLess(score, MIN_FILL_CONFIDENCE)

    def test_label_match_counts_as_strong(self):
        attrs = {"name": "q_42", "label": "Phone number"}
        self.assertGreaterEqual(score_field(attrs, ["phone"]), MIN_FILL_CONFIDENCE)

    def test_no_match_scores_zero(self):
        attrs = {"name": "favorite_color", "label": "Favorite color"}
        self.assertEqual(score_field(attrs, ["email", "phone"]), 0)

    def test_multiple_hints_accumulate(self):
        attrs = {"name": "linkedin_url", "placeholder": "LinkedIn profile URL"}
        # "linkedin" hits strong (2) and weak attrs hold it too; score reflects strong path.
        self.assertGreaterEqual(score_field(attrs, ["linkedin"]), 2)


if __name__ == "__main__":
    unittest.main()
