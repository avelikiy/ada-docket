#!/usr/bin/env python3
"""What the record holds, read from what we already measured. Spends nothing.

`make coverage` answers the same question by asking the court index again, at
one request a month — twenty-one of a daily allowance of a hundred and
twenty-five. That is the right way to *refresh* the answer and the wrong way to
*read* it, and the difference matters: three times in one session the honest
thing to do was check coverage before acting, and each time the only tool
available would have spent a sixth of the day's budget to re-derive numbers
already sitting in data/coverage.json.

A measurement worth taking is worth being able to re-read for free. Otherwise
the cheap habit is to skip the check, which is exactly how a truncated April
came to be published as a complete one.
"""

from __future__ import annotations

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import coverage  # noqa: E402

# Ordered worst-first: a reader scanning the top of the table should meet the
# months that are actually wrong before the ones that are merely unfinished.
SEVERITY = {
    coverage.PARTIAL: 0,
    coverage.UNKNOWN: 1,
    coverage.RECONCILED: 2,
    coverage.CURRENT: 3,
    coverage.COMPLETE: 4,
}

MARK = {
    coverage.PARTIAL: "!!",
    coverage.UNKNOWN: " ?",
    coverage.RECONCILED: " ~",
    coverage.CURRENT: " .",
    coverage.COMPLETE: " +",
}


def main() -> int:
    today = dt.date.today()
    doc = coverage.load()
    months = doc.get("months", {})
    if not months:
        print("no coverage recorded yet; run `make coverage` (spends requests)")
        return 1

    rows = []
    for ym in sorted(months):
        entry = months[ym]
        status = coverage.classify(entry, ym, today)
        api = entry.get("api_446") or 0
        have = entry.get("have_446") or 0
        rows.append((ym, status, api, have))

    held = sum(r[3] for r in rows)
    total = sum(r[2] for r in rows)
    counts: dict[str, int] = {}
    for _, status, _, _ in rows:
        counts[status] = counts.get(status, 0) + 1

    print(f"ada-docket coverage · read from data/coverage.json · {today}")
    print(
        f"  {held} of {total} filings across {len(rows)} months"
        f"  ({held / total * 100:.1f}%)"
        if total
        else "  no filings measured"
    )
    print()
    print("   month     source     held   short  status")
    for ym, status, api, have in sorted(
        rows, key=lambda r: (SEVERITY.get(r[1], 9), r[0])
    ):
        short = api - have
        print(
            f"{MARK.get(status, '  ')} {ym}   {api:>6}   {have:>6}  "
            f"{short if short > 0 else '':>6}  {status}"
        )
    print()
    print("  " + "  ".join(f"{s}: {n}" for s, n in sorted(counts.items())))

    # The one number cycle 6 set as its own finish line. Stated plainly so it
    # cannot be read off a wall of rows and got wrong.
    partial = counts.get(coverage.PARTIAL, 0)
    unknown = counts.get(coverage.UNKNOWN, 0)
    if partial or unknown:
        print(
            f"\n  {partial} month(s) short, {unknown} never audited — "
            "the record is not yet whole."
        )
    else:
        print("\n  Every audited month is accounted for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
