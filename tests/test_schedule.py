#!/usr/bin/env python3
"""Tests for the schedule anchor.

The bug these exist for shipped as a *comment*. `scripts/launchd.plist.in` said
"11:20 UTC matches the schedule the GitHub workflow asked for" directly above
`<key>Hour</key><integer>7</integer>`, and on a CEST machine that fires at
05:20 UTC — six hours before the PACER-to-RECAP indexing the anchor exists to
wait for. Nothing was broken enough to fail: launchd would have run happily,
every night, over a day the source had not finished indexing.

No test could have caught it, because there was nothing to call. The number was
a literal under a sentence, and a literal hour is unfalsifiable without a zone
beside it. So the fix is not "a more careful comment" — it is making the hour
something a machine computes and re-derives, which is the only form a test can
reach.

The timezone is forced here rather than inherited: a test that passes only in
the timezone that hid the bug is not a test.

Standard library only. `python3 -m unittest discover -s tests`.
"""

from __future__ import annotations

import datetime as dt
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import schedule  # noqa: E402

TEMPLATE = os.path.join(ROOT, "scripts", "launchd.plist.in")

# Two zones on opposite sides of the anchor, plus UTC itself. Europe/Berlin is
# the machine that shipped the bug; America/Los_Angeles converts the other way
# and lands the local slot on the previous calendar day.
ZONES = ["Europe/Berlin", "America/Los_Angeles", "UTC", "Asia/Tokyo"]

# One date in CET, one in CEST. If the conversion ignored DST, one of these
# would drift by an hour and the round-trip test would say so.
DATES = [dt.date(2026, 1, 15), dt.date(2026, 7, 15)]


class _InZone:
    """Run a block as if the machine were somewhere else."""

    def __init__(self, zone: str) -> None:
        self.zone = zone
        self.previous: str | None = None

    def __enter__(self) -> None:
        self.previous = os.environ.get("TZ")
        os.environ["TZ"] = self.zone
        time.tzset()

    def __exit__(self, *_exc: object) -> None:
        if self.previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self.previous
        time.tzset()


class AnchorConversion(unittest.TestCase):
    def test_computed_slot_lands_on_the_anchor_everywhere(self) -> None:
        """The whole contract: what we install fires at 11:20 UTC."""
        for zone in ZONES:
            for day in DATES:
                with self.subTest(zone=zone, day=day), _InZone(zone):
                    hour, minute = schedule.local_slot_for_utc(
                        schedule.ANCHOR_UTC_HOUR, schedule.ANCHOR_UTC_MINUTE, on=day
                    )
                    fires = schedule.utc_slot_for_local(hour, minute, on=day)
                    self.assertEqual(
                        fires,
                        (schedule.ANCHOR_UTC_HOUR, schedule.ANCHOR_UTC_MINUTE),
                        f"{zone} on {day}: {hour:02d}:{minute:02d} local "
                        f"fires at {fires[0]:02d}:{fires[1]:02d} UTC",
                    )
                    self.assertEqual(schedule.drift_minutes(hour, minute, on=day), 0)

    def test_dst_actually_moves_the_local_slot(self) -> None:
        """A conversion that ignored DST would return the same hour twice."""
        with _InZone("Europe/Berlin"):
            winter = schedule.local_slot_for_utc(
                schedule.ANCHOR_UTC_HOUR, schedule.ANCHOR_UTC_MINUTE, on=DATES[0]
            )
            summer = schedule.local_slot_for_utc(
                schedule.ANCHOR_UTC_HOUR, schedule.ANCHOR_UTC_MINUTE, on=DATES[1]
            )
        self.assertNotEqual(winter, summer, "CET and CEST cannot share a local slot")
        self.assertEqual((winter[0] + 1) % 24, summer[0])


class TheBugItself(unittest.TestCase):
    def test_literal_hour_seven_is_six_hours_early_in_cest(self) -> None:
        """The exact value that shipped, measured rather than remembered."""
        with _InZone("Europe/Berlin"):
            fires = schedule.utc_slot_for_local(7, 20, on=dt.date(2026, 9, 4))
            self.assertEqual(fires, (5, 20))
            self.assertEqual(
                schedule.drift_minutes(7, 20, on=dt.date(2026, 9, 4)), -360
            )

    def test_template_carries_no_literal_hour(self) -> None:
        """The invariant is checked at the input, not maintained by discipline.

        If someone re-types an hour into the template, this fails before the
        schedule silently fetches an unindexed day again.
        """
        with open(TEMPLATE, encoding="utf-8") as handle:
            body = handle.read()

        self.assertIn("__HOUR__", body)
        self.assertIn("__MINUTE__", body)

        interval = re.search(
            r"<key>StartCalendarInterval</key>\s*<dict>(.*?)</dict>", body, re.S
        )
        self.assertIsNotNone(interval, "template lost its StartCalendarInterval")
        self.assertNotRegex(
            interval.group(1),
            r"<integer>\s*\d+\s*</integer>",
            "a literal hour is back in the template; it must stay a placeholder",
        )


class ReadingWhatIsInstalled(unittest.TestCase):
    def _render(self, hour: int, minute: int) -> str:
        with open(TEMPLATE, encoding="utf-8") as handle:
            body = handle.read()
        body = (
            body.replace("__REPO__", ROOT)
            .replace("__HOUR__", str(hour))
            .replace("__MINUTE__", str(minute))
        )
        handle_fd, path = tempfile.mkstemp(suffix=".plist")
        with os.fdopen(handle_fd, "w", encoding="utf-8") as out:
            out.write(body)
        self.addCleanup(os.unlink, path)
        return path

    def test_rendered_template_is_a_valid_plist_we_can_read_back(self) -> None:
        path = self._render(13, 20)
        with open(path, "rb") as handle:
            loaded = plistlib.load(handle)
        self.assertEqual(loaded["Label"], "com.ada-docket.daily")
        self.assertIs(loaded["RunAtLoad"], False)
        self.assertEqual(schedule.read_plist_slot(path), (13, 20))

    def test_unsubstituted_template_is_not_mistaken_for_a_schedule(self) -> None:
        """`__HOUR__` is not an integer; the file must refuse to parse, not
        parse into some default."""
        with self.assertRaises(Exception):
            schedule.read_plist_slot(TEMPLATE)

    def test_plist_without_an_interval_is_an_error_not_a_guess(self) -> None:
        handle_fd, path = tempfile.mkstemp(suffix=".plist")
        with os.fdopen(handle_fd, "wb") as out:
            plistlib.dump({"Label": "x"}, out)
        self.addCleanup(os.unlink, path)
        with self.assertRaises(ValueError):
            schedule.read_plist_slot(path)


class TheCheckCommand(unittest.TestCase):
    def _check(self, hour: int, minute: int, zone: str) -> subprocess.CompletedProcess:
        handle_fd, path = tempfile.mkstemp(suffix=".plist")
        with os.fdopen(handle_fd, "wb") as out:
            plistlib.dump(
                {"StartCalendarInterval": {"Hour": hour, "Minute": minute}}, out
            )
        self.addCleanup(os.unlink, path)
        env = dict(os.environ, TZ=zone)
        return subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "scripts", "schedule.py"),
                "--check",
                path,
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_drifted_schedule_exits_non_zero_and_says_so(self) -> None:
        """`make schedule-status` has to be able to fail. A check that always
        passes is the same as no check."""
        result = self._check(7, 20, "Europe/Berlin")
        self.assertEqual(result.returncode, 1)
        self.assertIn("drift", result.stdout)
        self.assertIn("early", result.stdout)

    def test_correct_schedule_exits_zero(self) -> None:
        with _InZone("Europe/Berlin"):
            hour, minute = schedule.local_slot_for_utc(
                schedule.ANCHOR_UTC_HOUR, schedule.ANCHOR_UTC_MINUTE
            )
        result = self._check(hour, minute, "Europe/Berlin")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("none", result.stdout)

    def test_emit_local_prints_two_integers_the_makefile_can_split(self) -> None:
        env = dict(os.environ, TZ="Europe/Berlin")
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "scripts", "schedule.py"),
                "--emit-local",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        parts = result.stdout.split()
        self.assertEqual(len(parts), 2, result.stdout)
        hour, minute = (int(part) for part in parts)
        self.assertTrue(0 <= hour <= 23)
        self.assertEqual(minute, schedule.ANCHOR_UTC_MINUTE)


if __name__ == "__main__":
    unittest.main()
