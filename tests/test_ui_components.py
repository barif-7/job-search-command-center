"""Characterization tests for the UI render helpers extracted from app.py.

The golden fixture (fixtures_ui_golden.json) was captured from the original
in-app implementations. Every helper must reproduce that HTML byte-for-byte.
"""
import json
import unittest
from pathlib import Path

from jobsearch.ui import components as C

GOLDEN = json.loads((Path(__file__).parent / "fixtures_ui_golden.json").read_text(encoding="utf-8"))


class TestUiComponentsGolden(unittest.TestCase):
    def test_inline_initials(self):
        self.assertEqual(C.inline_initials("The New York Times"), GOLDEN["inline_initials"])

    def test_priority_badge(self):
        self.assertEqual(list(C.priority_badge(9)), GOLDEN["priority_badge_9"])
        self.assertEqual(list(C.priority_badge(7)), GOLDEN["priority_badge_7"])
        self.assertEqual(list(C.priority_badge(3)), GOLDEN["priority_badge_3"])
        self.assertEqual(list(C.priority_badge(0)), GOLDEN["priority_badge_0"])

    def test_logo_img_html(self):
        self.assertEqual(
            C.logo_img_html("OpenAI", "https://openai.com/careers/1", 48),
            GOLDEN["logo_img_html"],
        )

    def test_city_cover_config(self):
        self.assertEqual(C.city_cover_config("New York, NY"), GOLDEN["city_cover_config_nyc"])
        self.assertEqual(C.city_cover_config("Lagos"), GOLDEN["city_cover_config_default"])

    def test_city_cover_html(self):
        self.assertEqual(C.city_cover_html("Toronto"), GOLDEN["city_cover_html"])

    def test_metric_card_html_escapes(self):
        self.assertEqual(
            C.metric_card_html("Tracked roles", "42", "Latest <found>"),
            GOLDEN["metric_card_html"],
        )

    def test_surface_header_html(self):
        self.assertEqual(C.surface_header_html("Actions & stuff", "Do <things>"), GOLDEN["surface_header_html"])

    def test_hero_html(self):
        self.assertEqual(
            C.hero_html("Title & Co", "Copy <here>", ["a", "b&c"], eyebrow="Live"),
            GOLDEN["hero_html"],
        )

    def test_mini_role_html(self):
        self.assertEqual(
            C.mini_role_html("OpenAI", "iOS Eng", "SF", 8, "https://x.com/1"),
            GOLDEN["mini_role_html"],
        )
        self.assertEqual(
            C.mini_role_html("OpenAI", "iOS Eng", "", None, ""),
            GOLDEN["mini_role_html_noscore"],
        )

    def test_card_html(self):
        self.assertEqual(
            C.card_html("OpenAI", "iOS <Eng>", "https://x.com/1", "$200K", "SF", "lever", "Great **fit**", "Some concern", 9, "ai"),
            GOLDEN["card_html"],
        )

    def test_card_html_list(self):
        self.assertEqual(
            C.card_html_list("OpenAI", "iOS Eng", "https://x.com/1", "$200K", "SF", "lever", 7, "ios"),
            GOLDEN["card_html_list"],
        )

    def test_card_html_immersive(self):
        self.assertEqual(
            C.card_html_immersive("OpenAI", "iOS Eng", "https://x.com/1", "$200K", "Toronto", "lever", "Fit text", "Concern", 6, "new"),
            GOLDEN["card_html_immersive"],
        )


if __name__ == "__main__":
    unittest.main()
