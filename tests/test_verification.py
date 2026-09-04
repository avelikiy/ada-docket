#!/usr/bin/env python3
"""Tests for the search-engine verification tag.

This exists to shrink a human gate, not to add a feature. The project's whole
distribution hypothesis is long-tail search, and whether a single page has
ever been indexed is currently unknown and unknowable from here: a static
GitHub Pages site writes no logs, and the repository traffic API counts the
repository rather than the site.

The fix needs a person for about five minutes, and it has not happened for
three cycles. So the job is made as small as it can be: paste one token into
one file, run the publish that already runs daily. No build edit, no hunt for
where a <head> is assembled, no deciding between Google's four verification
methods.

The token is read from a file rather than an environment variable because the
publisher is launchd, which hands a job almost no environment — a variable
set in somebody's shell would verify by hand and then silently stop verifying
on the first scheduled run.
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

import build  # noqa: E402


class TestVerificationTag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "verification.txt")
        self._saved = build.VERIFICATION_PATH
        build.VERIFICATION_PATH = self.path

    def tearDown(self):
        build.VERIFICATION_PATH = self._saved

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_no_file_means_no_tag(self):
        """The default state must add nothing at all to the page."""
        self.assertEqual(build.verification_tags(), "")

    def test_a_token_becomes_a_meta_tag(self):
        self.write("abc123\n")
        self.assertIn('name="google-site-verification"', build.verification_tags())
        self.assertIn('content="abc123"', build.verification_tags())

    def test_surrounding_whitespace_is_forgiven(self):
        """Pasted tokens arrive with newlines and stray spaces."""
        self.write("   abc123  \n\n")
        self.assertIn('content="abc123"', build.verification_tags())

    def test_a_pasted_whole_meta_tag_still_works(self):
        """Google's console offers the entire tag; people paste what they are shown."""
        self.write('<meta name="google-site-verification" content="xyz789" />')
        out = build.verification_tags()
        self.assertIn('content="xyz789"', out)
        self.assertEqual(out.count("<meta"), 1)

    def test_comments_and_blanks_are_ignored(self):
        """The shipped file explains itself; its own prose is not a token."""
        self.write("# paste the token below\n\nabc123\n")
        out = build.verification_tags()
        self.assertIn('content="abc123"', out)
        self.assertNotIn("paste", out)

    def test_more_than_one_engine_is_allowed(self):
        """Bing Webmaster Tools uses the same shape; two lines, two tags."""
        self.write("google=abc123\nmsvalidate.01=DEF456\n")
        out = build.verification_tags()
        self.assertIn('name="google-site-verification" content="abc123"', out)
        self.assertIn('name="msvalidate.01" content="DEF456"', out)

    def test_a_token_is_escaped_not_trusted(self):
        self.write('ab"c><script>')
        out = build.verification_tags()
        self.assertNotIn("<script>", out)
        self.assertIn("&quot;", out)

    def test_the_tag_reaches_the_rendered_head(self):
        """The unit is only useful if page() actually emits it."""
        self.write("abc123\n")
        out = build.page(
            title="T",
            description="D",
            depth="",
            heading="H",
            standfirst="S",
            body="<p>x</p>",
        )
        head = out.split("</head>")[0]
        self.assertIn('content="abc123"', head)


if __name__ == "__main__":
    unittest.main()
