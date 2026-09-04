#!/usr/bin/env python3
"""Tests for optional CourtListener API authentication.

The rate ceiling is the single constraint that has shaped this project more
than any other. It truncated April 2025 into a one-day month, it stalled a
whole cycle's backfill, and closing the twelve-month hole anonymously takes
about four consecutive nights of a laptop being awake at the right minute.

fetch.py has carried the sentence "An API token would lift this" in its error
path for two cycles while offering no way whatsoever to supply one. This
closes that: a token is read if present and simply not used if absent.

Two properties matter more than the feature:

  - the token is a secret in a PUBLIC repository, so it is read from a
    gitignored file or the environment, and never written to a URL, a log, or
    a committed file;
  - nothing changes for a run without one. The anonymous path stays exactly
    as it was, because that is the path that will still be running tomorrow
    if nobody ever registers.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)

import fetch  # noqa: E402


class TokenCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "token")
        self._saved_path = fetch.TOKEN_PATH
        self._saved_env = os.environ.pop("COURTLISTENER_TOKEN", None)
        fetch.TOKEN_PATH = self.path

    def tearDown(self):
        fetch.TOKEN_PATH = self._saved_path
        os.environ.pop("COURTLISTENER_TOKEN", None)
        if self._saved_env is not None:
            os.environ["COURTLISTENER_TOKEN"] = self._saved_env

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)


class TestReadToken(TokenCase):
    def test_absent_is_none_not_empty_string(self):
        self.assertIsNone(fetch.read_token())

    def test_a_file_token_is_read_and_stripped(self):
        self.write("  abc123\n\n")
        self.assertEqual(fetch.read_token(), "abc123")

    def test_the_environment_wins_over_the_file(self):
        """A one-off run must be able to override without editing the file."""
        self.write("from-file")
        os.environ["COURTLISTENER_TOKEN"] = "from-env"
        self.assertEqual(fetch.read_token(), "from-env")

    def test_comments_and_blanks_are_ignored(self):
        """The shipped example file is all prose; it must not read as a token."""
        self.write("# paste your token here\n#\n\n")
        self.assertIsNone(fetch.read_token())

    def test_a_pasted_authorization_header_is_accepted(self):
        """People paste what the docs show them."""
        self.write("Authorization: Token abc123\n")
        self.assertEqual(fetch.read_token(), "abc123")

    def test_a_bare_token_prefix_is_accepted(self):
        self.write("Token abc123\n")
        self.assertEqual(fetch.read_token(), "abc123")


class TestHeaders(TokenCase):
    def test_no_token_sends_no_authorization(self):
        """The anonymous path must be untouched."""
        h = fetch.request_headers()
        self.assertNotIn("Authorization", h)
        self.assertIn("User-Agent", h)

    def test_a_token_becomes_an_authorization_header(self):
        self.write("abc123")
        self.assertEqual(fetch.request_headers()["Authorization"], "Token abc123")

    def test_the_token_never_goes_in_the_url(self):
        """A token in a query string leaks into logs and referrers."""
        self.write("abc123")
        self.assertNotIn("abc123", fetch.API)


class TestCeiling(TokenCase):
    def test_anonymous_keeps_the_documented_ceiling(self):
        self.assertEqual(fetch.hourly_max(), fetch.HOURLY_MAX_ANON)

    def test_a_token_raises_the_ceiling(self):
        self.write("abc123")
        self.assertGreater(fetch.hourly_max(), fetch.HOURLY_MAX_ANON)

    def test_the_raised_ceiling_is_still_a_ceiling(self):
        """Authenticated is not unlimited, and 429 must stay unreachable-by-design."""
        self.write("abc123")
        self.assertLess(fetch.hourly_max(), 100000)


if __name__ == "__main__":
    unittest.main()
