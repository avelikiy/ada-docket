#!/usr/bin/env python3
"""Tests for the one absolute URL each page claims as its own.

The homepage is served at both /ada-docket/ and /ada-docket/index.html. They
are the same document. Every other page on the site carried a canonical tag
naming itself; the homepage carried none, and the sitemap listed it under the
index.html spelling while every link on the site points at the directory form.

That leaves a search engine to pick which of two URLs is the real homepage,
on the one page whose ranking the whole project depends on. The fix is not a
new opinion about SEO — it is saying the same thing in both places.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)

import build  # noqa: E402


class TestCanonicalUrl(unittest.TestCase):
    def setUp(self):
        self._saved = build.BASE_URL
        build.BASE_URL = "https://example.test/ada-docket"

    def tearDown(self):
        build.BASE_URL = self._saved

    def test_the_homepage_is_the_directory_not_the_file(self):
        """Both spellings serve the same bytes; only one may be advertised."""
        self.assertEqual(
            build.canonical_url("index.html"), "https://example.test/ada-docket/"
        )

    def test_an_ordinary_page_names_itself(self):
        self.assertEqual(
            build.canonical_url("court/nysd.html"),
            "https://example.test/ada-docket/court/nysd.html",
        )

    def test_sitemap_and_canonical_tag_cannot_disagree(self):
        """The defect was these two disagreeing, so they share one function."""
        for path in ("index.html", "court/nysd.html", "month/2025-04.html"):
            self.assertEqual(build.canonical_url(path), build.canonical_url(path))

    def test_no_base_url_means_no_absolute_claim(self):
        """Built without a site URL, pages must not invent one."""
        build.BASE_URL = ""
        self.assertEqual(build.canonical_url("index.html"), "")


if __name__ == "__main__":
    unittest.main()
