#!/usr/bin/env python3
"""Tests for which files in data/ count as a filing partition.

This is the bug that killed a daily run. `pulse.py` wrote its readings to
data/pulse.ndjson; `fetch.load()` reads every *.ndjson in data/ as dockets, so
it met a reading, asked it for a docket_id, and died with a KeyError. The site
published anyway, because daily.sh continues past a failed fetch — so the
record silently stopped being daily while still claiming it was.

It was fixed by moving the readings to metrics/. That fixes the instance and
leaves the class: the readers still trust the directory rather than the
filename, so the next non-partition file dropped in data/ reproduces it
exactly. `save()` only ever writes YYYY-MM.ndjson, so that is the invariant
worth enforcing on the way back in.
"""

from __future__ import annotations

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

import backfill  # noqa: E402
import fetch  # noqa: E402


DOCKET = {
    "docket_id": 1,
    "dateFiled": "2025-01-02",
    "caseName": "A v. B",
    "court_id": "nysd",
}
READING = {"date": "2026-09-04", "subscribers": 0, "stars": 0, "cases": 2705}


class PartitionCase(unittest.TestCase):
    """Each test gets a data/ dir holding one real month and one intruder."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = fetch.DATA_DIR
        fetch.DATA_DIR = self.tmp
        self.write("2025-01.ndjson", DOCKET)

    def tearDown(self):
        fetch.DATA_DIR = self._saved

    def write(self, name, *rows):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")


class TestLoad(PartitionCase):
    def test_a_readings_file_does_not_kill_the_fetch(self):
        """The exact failure: KeyError 'docket_id' on 2026-09-04."""
        self.write("pulse.ndjson", READING)
        rows = fetch.load()
        self.assertEqual(list(rows), [1])

    def test_the_real_month_still_loads(self):
        self.assertEqual(list(fetch.load()), [1])

    def test_a_docket_missing_its_id_is_still_an_error(self):
        """Hardening the filename must not start swallowing corrupt dockets.

        A partition file whose rows lack docket_id means the writer is broken,
        and that has to stay loud. Only non-partition FILES are ignored.
        """
        self.write("2025-02.ndjson", {"caseName": "no id"})
        with self.assertRaises(KeyError):
            fetch.load()


class TestDataMonths(PartitionCase):
    def test_a_readings_file_is_not_a_month(self):
        """`data_months()` slices the name blind: 'pulse.ndjson'[:-7] == 'pulse'.

        That reaches coverage as a month, and a month named 'pulse' is then
        audited against the source — a wasted request answering nothing.
        """
        self.write("pulse.ndjson", READING)
        self.assertEqual(backfill.data_months(), ["2025-01"])

    def test_real_months_survive(self):
        self.write("2025-02.ndjson", DOCKET | {"docket_id": 2})
        self.assertEqual(backfill.data_months(), ["2025-01", "2025-02"])


if __name__ == "__main__":
    unittest.main()
