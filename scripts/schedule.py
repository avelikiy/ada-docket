#!/usr/bin/env python3
"""When the daily run fires, and whether that is still what we meant.

The schedule has one anchor and it is not a local wall-clock time. CourtListener
mirrors PACER overnight on US court time; 11:20 UTC was chosen because the
indexing has settled by then. That is a fact about other people's servers, so it
stays fixed in UTC while our clock moves.

launchd disagrees. `StartCalendarInterval` is interpreted in the machine's LOCAL
time, with no field for a zone. So the UTC anchor has to be converted at install
time — and the conversion is only true for the timezone and DST offset in force
on the day it ran.

That is exactly how this went wrong the first time. The template carried
`Hour 7`, and a comment stating it meant 11:20 UTC. On a machine in CEST it
meant 05:20 UTC: six hours early, before the indexing the anchor exists to wait
for. The comment and the file disagreed for a cycle and nobody could see it,
because reading the number tells you nothing without the zone.

So the number is computed, never typed, and `--check` re-derives it from the
installed file. A schedule that has drifted says so out loud instead of quietly
fetching yesterday's emptiness.

Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import plistlib
import sys

# The anchor. Everything else in this file is arithmetic around it.
ANCHOR_UTC_HOUR = 11
ANCHOR_UTC_MINUTE = 20

# Tolerated drift between what the installed plist fires at and the anchor.
# Zero: an hour of DST slide is a real hour, and the whole point is to notice.
DRIFT_TOLERANCE_MINUTES = 0


def local_slot_for_utc(
    hour: int, minute: int, on: dt.date | None = None
) -> tuple[int, int]:
    """The local wall-clock time that equals `hour:minute` UTC on `on`.

    `on` matters: the answer moves by an hour across a DST boundary, which is
    the whole reason this is a function and not a constant.
    """
    on = on or dt.date.today()
    moment = dt.datetime(
        on.year, on.month, on.day, hour, minute, tzinfo=dt.timezone.utc
    )
    local = moment.astimezone()
    return local.hour, local.minute


def utc_slot_for_local(
    hour: int, minute: int, on: dt.date | None = None
) -> tuple[int, int]:
    """The UTC time that a launchd local slot of `hour:minute` actually fires at."""
    on = on or dt.date.today()
    naive = dt.datetime(on.year, on.month, on.day, hour, minute)
    local = naive.astimezone()
    moment = local.astimezone(dt.timezone.utc)
    return moment.hour, moment.minute


def read_plist_slot(path: str) -> tuple[int, int]:
    """The (hour, minute) a `StartCalendarInterval` plist will fire at, local."""
    with open(path, "rb") as handle:
        loaded = plistlib.load(handle)
    interval = loaded.get("StartCalendarInterval")
    if not isinstance(interval, dict):
        raise ValueError(f"{path}: no StartCalendarInterval dict")
    if "Hour" not in interval or "Minute" not in interval:
        raise ValueError(f"{path}: StartCalendarInterval lacks Hour/Minute")
    return int(interval["Hour"]), int(interval["Minute"])


def drift_minutes(local_hour: int, local_minute: int, on: dt.date | None = None) -> int:
    """Signed minutes between where a local slot lands in UTC and the anchor.

    Wrapped into (-720, 720] so a slot just past midnight UTC reads as a small
    negative drift rather than a 23-hour one.
    """
    fires_h, fires_m = utc_slot_for_local(local_hour, local_minute, on=on)
    delta = (fires_h * 60 + fires_m) - (ANCHOR_UTC_HOUR * 60 + ANCHOR_UTC_MINUTE)
    return (delta + 720) % 1440 - 720


def _local_zone_name(on: dt.date | None = None) -> str:
    on = on or dt.date.today()
    return (
        dt.datetime(on.year, on.month, on.day, 12, 0).astimezone().tzname() or "local"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--emit-local",
        action="store_true",
        help="print the local 'HOUR MINUTE' that equals the UTC anchor today",
    )
    group.add_argument(
        "--check",
        metavar="PLIST",
        help="report what the installed plist really fires at, and any drift",
    )
    args = parser.parse_args(argv)

    if args.emit_local:
        hour, minute = local_slot_for_utc(ANCHOR_UTC_HOUR, ANCHOR_UTC_MINUTE)
        print(f"{hour} {minute}")
        return 0

    try:
        local_hour, local_minute = read_plist_slot(args.check)
    except (OSError, ValueError) as exc:
        print(f"schedule  unreadable — {exc}")
        return 1

    fires_h, fires_m = utc_slot_for_local(local_hour, local_minute)
    off = drift_minutes(local_hour, local_minute)
    zone = _local_zone_name()

    print(
        f"schedule  {local_hour:02d}:{local_minute:02d} {zone}"
        f"  =  {fires_h:02d}:{fires_m:02d} UTC"
        f"  (anchor {ANCHOR_UTC_HOUR:02d}:{ANCHOR_UTC_MINUTE:02d} UTC)"
    )

    if abs(off) <= DRIFT_TOLERANCE_MINUTES:
        print("drift     none — the run lands on the anchor")
        return 0

    early = "early" if off < 0 else "late"
    print(
        f"drift     {abs(off)} min {early} — the clock moved under the schedule.\n"
        f"          re-run `make schedule` to put it back on {ANCHOR_UTC_HOUR:02d}:"
        f"{ANCHOR_UTC_MINUTE:02d} UTC."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
