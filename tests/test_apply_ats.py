import unittest

from jobsearch.apply.ats import classify_blocker, detect_ats_provider, resolve_application_url


class TestApplyAts(unittest.TestCase):
    def test_resolve_lever_apply_url(self):
        url = "https://jobs.lever.co/textnow/abc123"
        self.assertEqual(resolve_application_url(url, "lever"), "https://jobs.lever.co/textnow/abc123/apply")

    def test_resolve_ashby_application_url(self):
        url = "https://jobs.ashbyhq.com/ramp/abc123"
        self.assertEqual(resolve_application_url(url, "ashby"), "https://jobs.ashbyhq.com/ramp/abc123/application")

    def test_detect_provider_prefers_board_when_host_is_generic(self):
        self.assertEqual(detect_ats_provider("https://example.com/job", "greenhouse"), "Greenhouse")

    def test_classify_captcha_blocker_from_text(self):
        self.assertEqual(classify_blocker("Please verify you are human before continuing"), "captcha")


if __name__ == "__main__":
    unittest.main()
