#!/usr/bin/env python3
"""Close the holes in the record, a day's worth of requests at a time.

There is a twelve-month hole between May 2025 and April 2026, and two months
that stop partway through. Both came from the same place: a backfill was started
by hand, ran into the hourly ceiling of fifty requests, and stopped. What
it left behind was not an error message but a plausible-looking short month, and
the site published that as fact for a cycle.

A backfill that cannot finish in one sitting is the normal case here, not the
exception. May 2025 alone reports 502 filings, and the search endpoint serves
twenty to a page, so a single month costs roughly twenty-nine requests and the
whole hole costs about four hundred. Against forty-five requests an hour that is
several nights' work. So this is written to be stopped: every month it finishes
is recorded, every run resumes from the record, and running out of budget is an
ordinary outcome that prints a plan rather than a traceback.

Two phases, in this order, because the order is what makes it cheap:

  audit    one request per month, comparing the count the source reports for
           that window against the rows we hold. Nine months cost nine requests
           and tell us exactly which months are actually broken.

  repair   crawl the months the audit found short, emptiest first, until the
           budget runs out.

Auditing first matters. Without it a backfill spends its whole day on the first
month in the list and never learns that four of the others were fine.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import coverage  # noqa: E402
import fetch  # noqa: E402

# CourtListener documents 125 requests a day for anonymous callers. The daily
# job needs a handful for its own ten-day window, and a run that spends the last
# request of the day on a backfill page leaves tomorrow's filings unfetched —
# the record would stop being daily in order to become complete, which is the
# wrong trade for a site whose entire claim is that it is current.
DAILY_CEILING = 125
RESERVED_FOR_DAILY_FETCH = 20

# The hourly ceiling, not the daily one, sets how long a run takes: 45 requests
# an hour means the full daily allowance would keep the job running for well
# over two hours. Two hours' worth is the cap, so a nightly run finishes in a
# predictable window and the rest waits for tomorrow. Nothing is lost by
# stopping — that is what the coverage record is for.
PER_RUN_MAX = 2 * fetch.HOURLY_MAX


def data_months() -> list[str]:
    """Months we hold a file for."""
    return sorted(
        os.path.basename(p)[:-7]
        for p in glob.glob(os.path.join(fetch.DATA_DIR, "*.ndjson"))
        # Name-matched, not merely suffix-matched. Slicing seven characters off
        # any *.ndjson turned pulse.ndjson into a month called "pulse", which
        # the audit would then spend a request asking the source about.
        if fetch.is_partition(os.path.basename(p))
        and os.path.basename(p)[:-7] != "unknown"
    )


def rows_for(ym: str) -> list[dict]:
    path = os.path.join(fetch.DATA_DIR, f"{ym}.ndjson")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def spent_today(doc: dict, today: str) -> int:
    return doc.get("spend", {}).get(today, 0)


def note_spend(doc: dict, today: str, n: int) -> None:
    spend = doc.setdefault("spend", {})
    spend[today] = spend.get(today, 0) + n
    # Keep the ledger short; only today's figure is ever read.
    for day in sorted(spend)[:-14]:
        del spend[day]


def source_count(ym: str) -> int:
    """How many 446 dockets the source reports for a month.

    One request. `count` is a property of the query, not of how many pages we
    chose to walk, which is exactly why it can detect a truncated crawl that the
    stored rows cannot.
    """
    since, until = coverage.month_bounds(ym)
    params = {
        "type": "r",
        "q": "suitNature:(446)",
        "filed_after": since,
        "filed_before": until,
        "order_by": "dateFiled desc",
    }
    data = fetch.get(fetch.API + "?" + urllib.parse.urlencode(params))
    return int(data.get("count") or 0)


# Results a page of the search endpoint returns. Measured, not assumed: a probe
# of May 2025 reported 502 filings and served twenty of them.
PAGE_SIZE = 20

# Pages the accommodations code adds on top of the ADA code. It is a small
# fraction of 446 in every month measured, but it is not nothing, and a cost
# estimate that ignores it would keep stopping a crawl just short of the end.
NOS_443_PAGES = 3


def month_cost(doc: dict, ym: str) -> int:
    """Roughly what a full crawl of one month costs, in requests."""
    entry = doc.get("months", {}).get(ym, {})
    api = entry.get("api_446") or 0
    return -(-api // PAGE_SIZE) + NOS_443_PAGES  # ceiling division


def audit(doc: dict, months: list[str], budget: int) -> int:
    """Measure each month against the source. Returns requests spent."""
    spent = 0
    for ym in months:
        if spent >= budget:
            print(f"  audit stopped at budget after {spent} requests")
            break
        try:
            api = source_count(ym)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("  audit hit the rate limit; stopping cleanly")
                break
            raise
        spent += 1
        rows = rows_for(ym)
        have = coverage.count_446(rows)
        last = max((r.get("dateFiled") or "" for r in rows), default="") or None
        coverage.record(doc, ym, api, have, last)
        status = coverage.classify(doc["months"][ym], ym)
        print(f"  {ym}  source {api:>4}  held {have:>4}  {status}", flush=True)
        # Written after every month, not at the end of the loop. An audit that
        # is interrupted — by the rate limit, by the laptop closing — should
        # keep the months it already measured, which is the same property the
        # backfill itself needs and for the same reason.
        coverage.save(doc)
        time.sleep(fetch.PAGE_PAUSE)
    return spent


def repair(doc: dict, ym: str, budget: int) -> tuple[int, int]:
    """Re-crawl one month in full. Returns (requests spent, filings added).

    The crawl is the existing one; nothing here is a second implementation of
    paging or of the ADA filter. A month is re-crawled from its first day rather
    than resumed from the last row we hold, because the source orders by filing
    date descending and a resumed crawl would silently skip anything indexed
    late into a window we had already passed.
    """
    since, until = coverage.month_bounds(ym)
    # The page ceiling is per nature-of-suit code, and the two codes are nothing
    # like the same size: a month holds five hundred 446 dockets and a handful of
    # 443 ones. Splitting the budget evenly between them gave 446 sixteen pages
    # where it needed twenty-six, so every repair truncated by construction and
    # the month it had just crawled stayed short. The ceiling is sized to the
    # month instead, and the caller has already checked the budget can afford it.
    entry = doc.get("months", {}).get(ym, {})
    max_pages = -(-(entry.get("api_446") or 0) // PAGE_SIZE) + NOS_443_PAGES
    # Still bounded by what the caller allowed, so a month whose count has grown
    # since the audit cannot quietly spend more than the run was given.
    max_pages = max(1, min(max_pages, budget))
    print(f"  repairing {ym} ({since} .. {until}), up to {max_pages} pages a code")

    before = fetch.load()
    mark = fetch.REQUESTS
    try:
        raw = fetch.crawl(since, until, max_pages)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print("  rate limit reached mid-repair; keeping what arrived")
            return fetch.REQUESTS - mark, 0
        raise

    existing = dict(before)
    # `first_seen` records when this record first saw a docket, not when it was
    # filed. A backfilled row is seen today; dating it to the end of the month
    # it belongs to would be a tidier-looking history and a false one.
    seen_today = dt.date.today().isoformat()
    added = 0
    for row in raw:
        did = row.get("docket_id")
        if did is None or not fetch.is_ada(row):
            continue
        rec = fetch.slim(row)
        if did not in existing:
            rec["first_seen"] = seen_today
            added += 1
        else:
            rec["first_seen"] = existing[did].get("first_seen", seen_today)
        existing[did] = rec

    fetch.save(existing)

    rows = rows_for(ym)
    have = coverage.count_446(rows)
    last = max((r.get("dateFiled") or "" for r in rows), default="") or None
    coverage.record(
        doc,
        ym,
        entry.get("api_446", have),
        have,
        last,
        full_crawl=not fetch.LAST_CRAWL_TRUNCATED,
    )
    spent = fetch.REQUESTS - mark
    print(f"  {ym}: +{added} filings, now hold {have} ({spent} requests)")
    return spent, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--budget",
        type=int,
        default=None,
        help="requests to spend this run (default: what is left of the day)",
    )
    ap.add_argument("--from", dest="first", default="2025-01", help="earliest month")
    ap.add_argument("--to", dest="last", default=None, help="latest month")
    ap.add_argument(
        "--audit-only",
        action="store_true",
        help="measure coverage and write it down; change no data",
    )
    ap.add_argument(
        "--plan",
        action="store_true",
        help="print what would be done, spend nothing",
    )
    args = ap.parse_args()

    today = dt.date.today()
    last = args.last or today.isoformat()[:7]
    doc = coverage.load()

    known = data_months()
    gap = coverage.missing_months(known, args.first, last)
    all_months = sorted(set(known) | set(gap))

    already = spent_today(doc, today.isoformat())
    allowance = DAILY_CEILING - RESERVED_FOR_DAILY_FETCH - already
    budget = args.budget if args.budget is not None else min(allowance, PER_RUN_MAX)
    budget = max(0, budget)

    print(f"ada-docket backfill · {today}")
    print(f"  months held      {len(known)}")
    print(
        f"  months missing   {len(gap)}" + (f"  ({gap[0]} .. {gap[-1]})" if gap else "")
    )
    print(f"  spent today      {already}/{DAILY_CEILING - RESERVED_FOR_DAILY_FETCH}")
    print(f"  budget this run  {budget} (about {budget / fetch.HOURLY_MAX:.1f} h)")

    if args.plan:
        needs = coverage.months_needing_work(doc, all_months, today)
        print(f"  would attend to  {len(needs)} months: {', '.join(needs[:12])}")
        return 0

    if budget <= 0:
        print("  nothing to spend today; the daily fetch keeps its reserve")
        return 0

    # Phase one: find out what is actually broken, cheaply.
    unaudited = [
        ym
        for ym in all_months
        if coverage.classify(doc.get("months", {}).get(ym), ym, today)
        == coverage.UNKNOWN
    ]
    spent = 0
    if unaudited:
        print(f"\naudit — {len(unaudited)} month(s) never measured")
        spent += audit(doc, unaudited, budget)
        coverage.save(doc)

    # Phase two: repair, emptiest month first.
    #
    # A month is attempted at most once per run. A crawl that completes and
    # still leaves the month short is possible — the source's reported count and
    # what its pagination actually yields need not agree — and without this the
    # loop would re-crawl that month until the day's entire budget was gone,
    # turning one odd month into a total outage of the backfill.
    attempted: set[str] = set()
    if not args.audit_only:
        while spent < budget:
            needs = [
                ym
                for ym in coverage.months_needing_work(doc, all_months, today)
                if ym not in attempted
            ]
            if not needs:
                break
            ym = needs[0]
            left = budget - spent

            # Do not start a month the budget cannot finish. A crawl cut off
            # part-way keeps the rows it fetched but leaves the month short, so
            # tomorrow re-walks the same pages from the beginning and pays for
            # them twice. Better to leave the requests unspent and start the
            # month whole tomorrow.
            need = month_cost(doc, ym)
            if need > left:
                print(
                    f"\n{ym} needs about {need} requests and {left} remain; "
                    f"leaving it for tomorrow rather than starting a crawl "
                    f"that cannot finish"
                )
                break
            print(f"\nrepair — {len(needs)} month(s) short")
            attempted.add(ym)
            used, _ = repair(doc, ym, left)
            spent += used
            coverage.save(doc)
            if used == 0:
                print(f"  {ym} spent nothing and is still short; stopping this run")
                break

    note_spend(doc, today.isoformat(), spent)
    coverage.save(doc)

    remaining = coverage.months_needing_work(doc, all_months, today)
    print(f"\nspent {spent} requests; {len(remaining)} month(s) still short")
    if remaining:
        print(f"  next: {remaining[0]} — the daily run continues automatically")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print(
                "CourtListener rate limit reached. Progress so far is recorded in "
                "data/coverage.json; the next run resumes from it.",
                file=sys.stderr,
            )
            sys.exit(2)
        raise
