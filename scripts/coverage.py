#!/usr/bin/env python3
"""How much of each month we actually hold, measured rather than assumed.

The site published two false numbers before this file existed. April 2025 said
"25 filings, 0.8 a day" when the real month had about five hundred, and May 2026
said "267 filings" for what was fifteen days of a thirty-one day month. Nothing
was wrong with either page's arithmetic. The pages counted the rows they were
given and reported the count correctly.

The defect was that coverage did not exist as a quantity. A backfill that stops
early — ours stopped at the anonymous rate ceiling of 125 requests a day —
leaves behind a month that is indistinguishable, downstream, from a quiet month.
The rows do not record what was asked for, only what came back, and an unasked
day and an empty day look identical once the request is over.

So coverage is measured against the source. The search endpoint reports a
`count` for any window, which is the number of dockets the query matches,
independent of how many pages we chose to walk. Comparing that count to what we
stored costs one request per month and answers the question directly: we hold
502 of 502, or we hold 25 of 502.

Nature-of-suit 446 is the yardstick because it is kept unconditionally — it is
the ADA code by definition. Code 443 is kept only when the cause of action cites
the ADA, so the stored count is legitimately lower than the reported count and
carries no information about truncation. Measuring against 446 alone keeps the
comparison exact.
"""

from __future__ import annotations

import calendar
import datetime as dt
import json
import os
from typing import Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
COVERAGE_PATH = os.path.join(DATA_DIR, "coverage.json")

VERSION = 1

# Statuses, in the order a reader would rank them.
COMPLETE = "complete"  # we hold every filing the source reports
CURRENT = "current"  # the month has not ended; complete so far
PARTIAL = "partial"  # measured against the source and short
UNKNOWN = "unknown"  # never audited; we cannot make any claim
RECONCILED = "reconciled"  # a filing or two short, at the source

# A month a filing or two below the count the index reports. Three real months
# came back like this — February 2025 held 521 of 522, June 2026 195 of 196,
# August 2026 331 of 332 — and the difference is at the source: the count and
# what pagination actually serves need not agree exactly.
#
# This status exists to stop the backfill re-crawling those months every day
# forever. Without it a month short by one costs twenty-six requests a night, in
# perpetuity, to fetch nothing. Treating it as complete is also the truthful
# reading: we hold everything the source will give us.
RECONCILE_TOLERANCE = 3


def month_days(ym: str) -> int:
    """Calendar days in a YYYY-MM month."""
    year, month = (int(x) for x in ym.split("-"))
    return calendar.monthrange(year, month)[1]


def month_bounds(ym: str) -> tuple[str, str]:
    """First and last day of a month, as ISO dates, inclusive."""
    year, month = (int(x) for x in ym.split("-"))
    return f"{ym}-01", f"{ym}-{month_days(ym):02d}"


def is_current_month(ym: str, today: dt.date | None = None) -> bool:
    today = today or dt.date.today()
    return ym == today.isoformat()[:7]


def classify(entry: dict | None, ym: str, today: dt.date | None = None) -> str:
    """What we are entitled to say about one month.

    A month never audited is `unknown`, not `complete`. That asymmetry is the
    whole point: silence about coverage must not read as a clean bill of health,
    which is precisely how the April 2025 page came to state a confident number.
    """
    if not entry or entry.get("api_446") is None:
        return UNKNOWN

    api = entry["api_446"]
    have = entry.get("have_446", 0)

    # The source can index a docket after we counted it, so holding more than
    # the last audit reported is normal and is not a discrepancy.
    if have < api:
        # A shortfall this small cannot be truncation. Pages hold twenty, so a
        # crawl that stops early loses filings twenty at a time; it cannot leave
        # us one short. The residual is a disagreement at the source between the
        # count and what pagination serves, and `full_crawl` is recorded but not
        # required — demanding it would have left August 2026, which holds 331 of
        # 332, drawn as a month we had never collected.
        if (api - have) <= RECONCILE_TOLERANCE:
            return RECONCILED
        return PARTIAL
    return CURRENT if is_current_month(ym, today) else COMPLETE


def held_fraction(entry: dict | None) -> float | None:
    """Share of the source's count we hold, or None if never audited."""
    if not entry or not entry.get("api_446"):
        return None
    return min(1.0, entry.get("have_446", 0) / entry["api_446"])


def covered_through(entry: dict | None) -> str | None:
    """Last filing date we actually hold for the month, if recorded."""
    return (entry or {}).get("last_filing")


def load(path: str = COVERAGE_PATH) -> dict:
    """Read the coverage record. A missing file is an empty record, not an
    error: every month is then `unknown`, which is the honest starting state."""
    if not os.path.exists(path):
        return {"version": VERSION, "months": {}}
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc.setdefault("months", {})
    doc.setdefault("version", VERSION)
    return doc


def save(doc: dict, path: str = COVERAGE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def record(
    doc: dict,
    ym: str,
    api_446: int,
    have_446: int,
    last_filing: str | None,
    checked: str | None = None,
    full_crawl: bool | None = None,
) -> dict:
    """Write one month's audit result into the record.

    `full_crawl` is sticky: a later cheap audit re-measures the counts but does
    not walk the pages, and it must not erase the fact that a crawl once ran to
    exhaustion — that would send the backfill back to a month it had finished.
    """
    prior = doc.setdefault("months", {}).get(ym, {})
    doc["months"][ym] = {
        "api_446": api_446,
        "have_446": have_446,
        "last_filing": last_filing,
        "full_crawl": prior.get("full_crawl", False)
        if full_crawl is None
        else full_crawl,
        "checked": checked
        or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return doc


def count_446(rows: Iterable[dict]) -> int:
    """Rows stored under nature-of-suit 446, the code kept unconditionally."""
    return sum(1 for r in rows if (r.get("suitNature") or "").strip().startswith("446"))


def months_needing_work(
    doc: dict, known_months: Iterable[str], today: dt.date | None = None
) -> list[str]:
    """Months a backfill should attend to, neediest first.

    `unknown` outranks `partial` because an unaudited month costs one request to
    classify and may need nothing further, while a partial month costs dozens.
    Establishing what is actually broken before spending the day's budget on it
    is the cheaper order.
    """
    today = today or dt.date.today()
    months = doc.get("months", {})
    ranked: list[tuple[int, float, str]] = []
    for ym in known_months:
        status = classify(months.get(ym), ym, today)
        if status in (COMPLETE, CURRENT, RECONCILED):
            continue
        rank = 0 if status == UNKNOWN else 1
        # Among partial months, the emptiest first: it is the one whose page is
        # telling the largest lie right now.
        ranked.append((rank, held_fraction(months.get(ym)) or 0.0, ym))
    ranked.sort(key=lambda t: (t[0], t[1], t[2]))
    return [ym for _, _, ym in ranked]


def missing_months(known: Iterable[str], first: str, last: str) -> list[str]:
    """Calendar months between `first` and `last` with no data file at all.

    A month with no file is invisible to any check that iterates over what we
    hold — the twelve-month hole from May 2025 to April 2026 produced no pages,
    no warnings and no rows, and so went unnoticed until someone listed the
    directory by hand.
    """
    have = set(known)
    out: list[str] = []
    y, m = (int(x) for x in first.split("-"))
    ly, lm = (int(x) for x in last.split("-"))
    while (y, m) <= (ly, lm):
        ym = f"{y:04d}-{m:02d}"
        if ym not in have:
            out.append(ym)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out
