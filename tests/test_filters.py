import unittest
from jobsearch.config import LOCATION_KEYWORDS, ROLE_KEYWORDS

class TestFilters(unittest.TestCase):
    def test_defaults(self):
        self.assertTrue(len(LOCATION_KEYWORDS) > 0)
        self.assertTrue(len(ROLE_KEYWORDS) > 0)
