"""Characterization tests for logo/domain resolution extracted from app.py.

Golden values captured from the original in-app implementation (with no
LOGO_DEV_TOKEN set, matching the default environment).
"""
import unittest

from jobsearch.services import logo_service as L


class TestResolveDomain(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(L.normalize_company_name("  The   New York Times "), "the new york times")

    def test_known_company(self):
        self.assertEqual(L.resolve_company_domain("The New York Times"), "nytimes.com")

    def test_domain_from_non_board_url(self):
        self.assertEqual(
            L.resolve_company_domain("Unknown Co", "https://careers.unknownco.com/jobs/1"),
            "careers.unknownco.com",
        )

    def test_board_url_is_ignored_falls_back_to_slug(self):
        self.assertEqual(
            L.resolve_company_domain("Some Startup", "https://jobs.lever.co/some/1"),
            "somestartup.com",
        )

    def test_slug_fallback_strips_punctuation(self):
        self.assertEqual(L.resolve_company_domain("Brand New Co!!!", ""), "brandnewco.com")

    def test_empty_company(self):
        self.assertEqual(L.resolve_company_domain("", ""), "")


class TestUrlBuilders(unittest.TestCase):
    def test_favicon_url(self):
        self.assertEqual(
            L.google_favicon_url("openai.com", 64),
            "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://openai.com&size=64",
        )

    def test_base_url_without_token(self):
        self.assertFalse(L.LOGO_DEV_TOKEN)  # default env has no token
        self.assertEqual(L.base_logo_url("openai.com", 48), "https://img.logo.dev/openai.com?format=png&size=48")


class TestLogoSources(unittest.TestCase):
    def test_known_company_sources(self):
        sources = L.logo_sources("OpenAI", "", 64)
        self.assertEqual(sources[0], "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://openai.com&size=64")
        self.assertEqual(sources[1], "https://www.google.com/s2/favicons?sz=64&domain=openai.com")
        # No logo.dev entry without a token; two URLs per candidate domain.
        self.assertTrue(all("img.logo.dev" not in s for s in sources))
        self.assertEqual(len(sources), 14)  # 7 domain guesses × 2 URLs

    def test_url_domain_leads(self):
        sources = L.logo_sources("Weird Name", "https://careers.acme.io/1", 32)
        self.assertIn("url=http://careers.acme.io&size=32", sources[0])

    def test_logo_url_returns_primary(self):
        self.assertEqual(
            L.logo_url("OpenAI"),
            "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://openai.com&size=40",
        )

    def test_token_path_adds_logo_dev(self):
        original = L.LOGO_DEV_TOKEN
        L.LOGO_DEV_TOKEN = "tok123"
        try:
            sources = L.logo_sources("OpenAI", "", 64)
            self.assertIn("https://img.logo.dev/openai.com?format=png&size=64&token=tok123", sources)
        finally:
            L.LOGO_DEV_TOKEN = original


if __name__ == "__main__":
    unittest.main()
