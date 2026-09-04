#!/usr/bin/env python3
"""Tests for the coverage model.

The project has found every one of its bugs by running code, never by reading
it: four in cycle four, two more here. That record is an argument for tests
rather than against them, and coverage is the first thing that cannot be checked
by eye — a truncated month looks exactly like a quiet one on the page, which is
how it survived a build, a publish and a review.

Standard library only, same as the rest of the project. `python3 -m unittest
discover -s tests` and nothing to install.
"""

from __future__ import annotations

import datetime as dt
import json
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

import coverage  # noqa: E402


APRIL = dt.date(2026, 9, 4)  # a fixed "today" so the tests do not drift


class TestClassify(unittest.TestCase):
    def test_never_audited_is_unknown_not_complete(self):
        """Silence must not read as a clean bill of health.

        This is the bug that shipped: the April 2025 page had no coverage
        information and stated a confident number anyway.
        """
        self.assertEqual(coverage.classify(None, "2025-04", APRIL), coverage.UNKNOWN)
        self.assertEqual(coverage.classify({}, "2025-04", APRIL), coverage.UNKNOWN)

    def test_short_month_is_partial(self):
        entry = {"api_446": 502, "have_446": 25}
        self.assertEqual(coverage.classify(entry, "2025-04", APRIL), coverage.PARTIAL)

    def test_full_past_month_is_complete(self):
        entry = {"api_446": 502, "have_446": 502}
        self.assertEqual(coverage.classify(entry, "2025-04", APRIL), coverage.COMPLETE)

    def test_holding_more_than_source_reported_is_not_a_discrepancy(self):
        """The source indexes dockets after we count them; that is not truncation."""
        entry = {"api_446": 500, "have_446": 503}
        self.assertEqual(coverage.classify(entry, "2025-04", APRIL), coverage.COMPLETE)

    def test_current_month_is_current_not_complete(self):
        entry = {"api_446": 32, "have_446": 32}
        self.assertEqual(coverage.classify(entry, "2026-09", APRIL), coverage.CURRENT)

    def test_current_month_can_still_be_partial(self):
        entry = {"api_446": 90, "have_446": 32}
        self.assertEqual(coverage.classify(entry, "2026-09", APRIL), coverage.PARTIAL)


class TestReconciled(unittest.TestCase):
    """February 2025 holds 521 of the 522 the index reports, after a crawl that
    walked every page. Without a way to say so, the backfill would spend
    twenty-six requests a night on that month for ever."""

    def test_a_hair_short_is_reconciled(self):
        entry = {"api_446": 522, "have_446": 521, "full_crawl": True}
        self.assertEqual(
            coverage.classify(entry, "2025-02", APRIL), coverage.RECONCILED
        )

    def test_a_truncated_month_is_never_reconciled(self):
        """April 2025 held 24 of 409 after a crawl that ran out of budget.

        A gap of that size is whole pages missing, which is exactly what the
        reconciliation must never absorb.
        """
        entry = {"api_446": 409, "have_446": 24, "full_crawl": False}
        self.assertEqual(coverage.classify(entry, "2025-04", APRIL), coverage.PARTIAL)

    def test_a_shortfall_of_one_needs_no_full_crawl(self):
        """Pages hold twenty, so truncation cannot leave a month one short.

        August 2026 holds 331 of 332 and had not been re-crawled; requiring a
        full crawl drew the site's most recent weeks as never collected.
        """
        entry = {"api_446": 332, "have_446": 331}
        self.assertEqual(
            coverage.classify(entry, "2026-08", APRIL), coverage.RECONCILED
        )

    def test_one_short_of_a_page_is_still_partial(self):
        entry = {"api_446": 400, "have_446": 380}
        self.assertEqual(coverage.classify(entry, "2025-04", APRIL), coverage.PARTIAL)

    def test_a_large_shortfall_is_partial_even_after_a_full_crawl(self):
        entry = {"api_446": 500, "have_446": 400, "full_crawl": True}
        self.assertEqual(coverage.classify(entry, "2025-04", APRIL), coverage.PARTIAL)

    def test_reconciled_months_are_not_work(self):
        doc = {
            "months": {"2025-02": {"api_446": 522, "have_446": 521, "full_crawl": True}}
        }
        self.assertEqual(coverage.months_needing_work(doc, ["2025-02"], APRIL), [])

    def test_full_crawl_survives_a_later_cheap_audit(self):
        """A re-audit re-counts but does not re-walk; it must not undo the crawl."""
        doc = coverage.record({}, "2025-02", 522, 521, "2025-02-28", full_crawl=True)
        coverage.record(doc, "2025-02", 522, 521, "2025-02-28")  # audit, no crawl
        self.assertTrue(doc["months"]["2025-02"]["full_crawl"])
        self.assertEqual(
            coverage.classify(doc["months"]["2025-02"], "2025-02", APRIL),
            coverage.RECONCILED,
        )


class TestFraction(unittest.TestCase):
    def test_unaudited_has_no_fraction(self):
        self.assertIsNone(coverage.held_fraction(None))
        self.assertIsNone(coverage.held_fraction({"api_446": 0}))

    def test_fraction_is_capped_at_one(self):
        self.assertEqual(coverage.held_fraction({"api_446": 100, "have_446": 130}), 1.0)

    def test_fraction_of_the_real_april_gap(self):
        self.assertAlmostEqual(
            coverage.held_fraction({"api_446": 502, "have_446": 25}), 25 / 502
        )


class TestMonthArithmetic(unittest.TestCase):
    def test_days_in_month(self):
        self.assertEqual(coverage.month_days("2025-04"), 30)
        self.assertEqual(coverage.month_days("2025-02"), 28)
        self.assertEqual(coverage.month_days("2024-02"), 29)  # leap
        self.assertEqual(coverage.month_days("2026-05"), 31)

    def test_bounds(self):
        self.assertEqual(coverage.month_bounds("2025-04"), ("2025-04-01", "2025-04-30"))
        self.assertEqual(coverage.month_bounds("2026-02"), ("2026-02-01", "2026-02-28"))


class TestCount446(unittest.TestCase):
    def test_counts_only_the_unconditional_code(self):
        rows = [
            {"suitNature": "446 Civil Rights: Americans with Disabilities - Other"},
            {"suitNature": "443 Civil Rights: Accommodations"},
            {"suitNature": "446 something"},
            {"suitNature": None},
            {},
        ]
        self.assertEqual(coverage.count_446(rows), 2)


class TestPriority(unittest.TestCase):
    def test_unknown_months_come_before_partial_ones(self):
        """One request classifies an unknown month; dozens repair a partial one.

        Spending the day's budget before knowing what is broken is the more
        expensive order, so unknown sorts first.
        """
        doc = {
            "months": {
                "2025-04": {"api_446": 502, "have_446": 25},
                "2026-05": {"api_446": 500, "have_446": 267},
            }
        }
        order = coverage.months_needing_work(
            doc, ["2025-04", "2026-05", "2025-09"], APRIL
        )
        self.assertEqual(order[0], "2025-09")  # unaudited
        self.assertEqual(order[1], "2025-04")  # emptiest partial
        self.assertEqual(order[2], "2026-05")

    def test_complete_months_are_not_work(self):
        doc = {"months": {"2025-01": {"api_446": 524, "have_446": 524}}}
        self.assertEqual(coverage.months_needing_work(doc, ["2025-01"], APRIL), [])

    def test_current_month_is_not_work_when_it_is_caught_up(self):
        doc = {"months": {"2026-09": {"api_446": 32, "have_446": 32}}}
        self.assertEqual(coverage.months_needing_work(doc, ["2026-09"], APRIL), [])


class TestMissingMonths(unittest.TestCase):
    def test_finds_the_real_twelve_month_hole(self):
        """The gap that produced no rows, no pages and no warning."""
        have = [
            "2025-01",
            "2025-02",
            "2025-03",
            "2025-04",
            "2026-05",
            "2026-06",
            "2026-07",
            "2026-08",
            "2026-09",
        ]
        gap = coverage.missing_months(have, "2025-01", "2026-09")
        self.assertEqual(len(gap), 12)
        self.assertEqual(gap[0], "2025-05")
        self.assertEqual(gap[-1], "2026-04")

    def test_crosses_the_year_boundary(self):
        gap = coverage.missing_months(["2025-11"], "2025-11", "2026-02")
        self.assertEqual(gap, ["2025-12", "2026-01", "2026-02"])

    def test_nothing_missing(self):
        self.assertEqual(coverage.missing_months(["2025-01"], "2025-01", "2025-01"), [])


class TestRoundTrip(unittest.TestCase):
    def test_record_survives_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "coverage.json")
            doc = coverage.load(path)
            self.assertEqual(doc["months"], {})  # missing file is empty, not an error

            coverage.record(doc, "2025-04", 502, 25, "2025-04-01")
            coverage.save(doc, path)

            again = coverage.load(path)
            self.assertEqual(again["months"]["2025-04"]["api_446"], 502)
            self.assertEqual(again["months"]["2025-04"]["have_446"], 25)
            self.assertEqual(
                coverage.classify(again["months"]["2025-04"], "2025-04", APRIL),
                coverage.PARTIAL,
            )

    def test_save_is_atomic_enough_to_leave_no_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "coverage.json")
            coverage.save(
                coverage.record(coverage.load(path), "2025-01", 1, 1, None), path
            )
            self.assertFalse(os.path.exists(path + ".tmp"))
            json.load(open(path, encoding="utf-8"))  # parses


if __name__ == "__main__":
    unittest.main()
