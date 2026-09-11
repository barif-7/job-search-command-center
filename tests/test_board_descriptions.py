"""Board fetchers must populate `description`.

All three previously hardcoded it to "", which left keyword extraction reading
nothing but job titles. These tests pin the parsing against captured API
payload shapes — no network.
"""
import asyncio
import unittest

from jobsearch.boards import description_text
from jobsearch.boards.ashby import AshbyFetcher
from jobsearch.boards.greenhouse import GreenhouseFetcher
from jobsearch.boards.lever import LeverFetcher


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeClient:
    """Routes GETs by URL substring; records the params each call passed."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    async def get(self, url, params=None, **kwargs):
        self.calls.append((url, params))
        for fragment, response in self.routes.items():
            if fragment in url:
                return response
        return FakeResponse(status_code=404)


class TestDescriptionText(unittest.TestCase):
    def test_unescapes_strips_and_collapses(self):
        raw = "&lt;p&gt;Build &lt;b&gt;iOS&lt;/b&gt; apps   with Swift &amp;amp; Python.&lt;/p&gt;"
        self.assertEqual(description_text(raw), "Build iOS apps with Swift & Python.")

    def test_drops_script_and_style_bodies(self):
        raw = "<p>Uses AWS</p><script>var x = 1</script><style>a{color:red}</style><p>and Docker</p>"
        self.assertEqual(description_text(raw), "Uses AWS and Docker")

    def test_empty_input_is_empty_string(self):
        self.assertEqual(description_text(None), "")
        self.assertEqual(description_text(""), "")

    def test_truncates_very_long_descriptions(self):
        from jobsearch.boards import MAX_DESCRIPTION_CHARS
        self.assertEqual(len(description_text("x" * (MAX_DESCRIPTION_CHARS + 500))),
                         MAX_DESCRIPTION_CHARS)


class TestGreenhouseDescription(unittest.TestCase):
    def _fetch(self, client):
        return asyncio.run(GreenhouseFetcher().fetch(
            client, {"api_base": "https://gh.test", "companies": {"acme": "Acme"}}
        ))

    def test_requests_content_and_populates_description(self):
        client = FakeClient({"gh.test": FakeResponse({"jobs": [{
            "title": "iOS Engineer",
            "location": {"name": "San Francisco"},
            "absolute_url": "https://gh.test/acme/1",
            "content": "&lt;p&gt;Swift, SwiftUI and &lt;b&gt;AWS&lt;/b&gt;.&lt;/p&gt;",
        }]})})
        result = self._fetch(client)
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0]["description"], "Swift, SwiftUI and AWS.")
        # Without content=true the API returns no body at all.
        self.assertEqual(client.calls[0][1], {"content": "true"})

    def test_missing_content_degrades_to_empty(self):
        client = FakeClient({"gh.test": FakeResponse({"jobs": [{
            "title": "iOS Engineer",
            "location": {"name": "San Francisco"},
            "absolute_url": "https://gh.test/acme/1",
        }]})})
        self.assertEqual(self._fetch(client).jobs[0]["description"], "")


class TestLeverDescription(unittest.TestCase):
    def test_joins_body_lists_and_additional(self):
        client = FakeClient({"lever.test": FakeResponse([{
            "text": "iOS Engineer",
            "categories": {"location": "New York"},
            "hostedUrl": "https://lever.test/acme/1",
            "descriptionPlain": "Build the iOS app.",
            "lists": [{"text": "Requirements", "content": "<li>Swift</li><li>Docker</li>"}],
            "additionalPlain": "We use Kubernetes.",
        }])})
        result = asyncio.run(LeverFetcher().fetch(
            client, {"api_base": "https://lever.test", "companies": {"acme": "Acme"}}
        ))
        desc = result.jobs[0]["description"]
        # All three sources land in the text keyword extraction reads.
        for token in ("Build the iOS app.", "Requirements", "Swift", "Docker", "Kubernetes"):
            self.assertIn(token, desc)


class TestAshbyDescription(unittest.TestCase):
    POSTING = {
        "id": "abc",
        "title": "iOS Engineer",
        "location": "San Francisco",
        "secondaryLocations": [{"location": "New York"}],
        "jobUrl": "https://jobs.ashbyhq.com/acme/abc",
        "descriptionPlain": "Swift and Kubernetes.",
        "isListed": True,
    }

    def _fetch(self, client):
        return asyncio.run(AshbyFetcher().fetch(client, {
            "api_base": "https://jobs.ashbyhq.com",
            "posting_api_base": "https://api.test/job-board",
            "companies": {"acme": "Acme"},
        }))

    def test_posting_api_supplies_description_and_locations(self):
        client = FakeClient({"api.test": FakeResponse({"jobs": [self.POSTING]})})
        job = self._fetch(client).jobs[0]
        self.assertEqual(job["description"], "Swift and Kubernetes.")
        self.assertEqual(job["location"], "San Francisco / New York")
        self.assertEqual(job["url"], "https://jobs.ashbyhq.com/acme/abc")

    def test_url_matches_the_html_path_so_dedupe_survives(self):
        """The two sources must agree on URL or a switch double-inserts."""
        api_client = FakeClient({"api.test": FakeResponse({"jobs": [self.POSTING]})})
        html = '<html>{"jobPostings": [{"id": "abc", "title": "iOS Engineer", ' \
               '"locationName": "San Francisco", "secondaryLocations": []}]}</html>'
        html_client = FakeClient({"api.test": FakeResponse(status_code=404),
                                  "jobs.ashbyhq.com": FakeResponse(text=html)})
        self.assertEqual(self._fetch(api_client).jobs[0]["url"],
                         self._fetch(html_client).jobs[0]["url"])

    def test_falls_back_to_html_when_posting_api_missing(self):
        html = '<html>{"jobPostings": [{"id": "abc", "title": "iOS Engineer", ' \
               '"locationName": "San Francisco", "secondaryLocations": []}]}</html>'
        client = FakeClient({"api.test": FakeResponse(status_code=404),
                             "jobs.ashbyhq.com": FakeResponse(text=html)})
        result = self._fetch(client)
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.companies_failed, 0)
        # The HTML path has no body to offer, but the job is still captured.
        self.assertEqual(result.jobs[0]["description"], "")

    def test_company_counts_as_failed_only_when_both_paths_fail(self):
        client = FakeClient({"api.test": FakeResponse(status_code=500),
                             "jobs.ashbyhq.com": FakeResponse(status_code=500)})
        result = self._fetch(client)
        self.assertEqual(result.companies_failed, 1)
        self.assertEqual(result.jobs, [])

    def test_unlisted_postings_are_skipped(self):
        hidden = dict(self.POSTING, isListed=False)
        client = FakeClient({"api.test": FakeResponse({"jobs": [hidden]})})
        self.assertEqual(self._fetch(client).jobs, [])



class TestRoleMatching(unittest.TestCase):
    """Role criteria broadened beyond iOS on 2026-09-02; exclusions keep the
    generic keywords ("software engineer") to IC engineering titles."""

    def test_specialised_ic_titles_match(self):
        from jobsearch.boards import matches_role
        for title in (
            "Senior iOS Engineer",
            "Staff Backend Engineer",
            "Senior Software Engineer, Payments",
            "Machine Learning Engineer",
            "Full-Stack Engineer, Growth",
            "Platform Engineer",
            "Forward Deployed Engineer",
            "Senior Software Engineer (iOS), SDK",
        ):
            self.assertTrue(matches_role(title), title)

    def test_non_ic_titles_are_excluded(self):
        from jobsearch.boards import matches_role
        for title in (
            "Engineering Manager, Platform",
            "Director of Software Engineering",
            "Software Engineer Intern",
            "Software Engineer, New Grad",
            "Sales Engineer",
            "Solutions Engineer, Enterprise",
            "Head of Software Engineering",
            "VP, Engineering",
        ):
            self.assertFalse(matches_role(title), title)

    def test_unrelated_titles_do_not_match(self):
        from jobsearch.boards import matches_role
        for title in ("Product Designer", "Office Manager", "Account Executive"):
            self.assertFalse(matches_role(title), title)

    def test_exclusion_beats_keyword(self):
        """Both a keyword and an exclusion present — exclusion must win."""
        from jobsearch.boards import matches_role
        self.assertFalse(matches_role("Software Engineer Manager"))

    def test_location_filter(self):
        from jobsearch.boards import location_wanted
        self.assertTrue(location_wanted("Toronto, Ontario, Canada"))
        self.assertTrue(location_wanted("Remote - United States"))
        self.assertFalse(location_wanted("London, United Kingdom"))
        self.assertFalse(location_wanted(""))

if __name__ == "__main__":
    unittest.main()
