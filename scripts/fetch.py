#!/usr/bin/env python3
"""Incremental ingest of federal ADA Title III filings from the CourtListener API.

Source: https://www.courtlistener.com/api/rest/v4/search/?type=r
The v4 search endpoint serves RECAP dockets to anonymous clients. Federal court
records are public; CourtListener is credited on every row of the published site.

Writes newline-delimited JSON to data/cases.ndjson, keyed on docket_id so that
re-running the job never duplicates a case. Standard library only: the daily job
runs on a stock GitHub Actions runner with no install step.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.courtlistener.com/api/rest/v4/search/"

# CourtListener documents three ceilings: 5 requests a minute, 50 an hour, 125 a
# day. A 13-second pause honours the first and quietly breaks the second — it
# works out at 277 requests an hour. That is why the original backfill died
# part-way through April 2025 and left the month one day long: it was not the
# daily ceiling that stopped it but the hourly one, about fifty requests in, and
# the 429s that followed looked like a hang rather than a limit.
#
# So the spacing is a floor, not the whole policy, and the hourly ceiling is
# enforced below on a rolling window. The daily job makes about four requests
# and never notices either.
PAGE_PAUSE = 13.0

# Requests allowed per rolling hour, against a documented fifty. The margin
# covers the daily fetch running alongside a backfill.
HOURLY_MAX = 45

# The window has to outlive the process. The daily loop runs the fetch and the
# backfill as two separate programs within a minute of each other, and a limiter
# that starts empty in each of them would let the pair spend ninety requests in
# an hour while both believed they were being careful.
_WINDOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".requests"
)


def _read_window() -> list[float]:
    try:
        with open(_WINDOW_PATH, encoding="utf-8") as fh:
            stamps = json.load(fh)
    except (OSError, ValueError):
        return []
    cutoff = time.time() - 3600
    return [t for t in stamps if isinstance(t, (int, float)) and t > cutoff]


def _await_slot() -> None:
    """Block until a request would stay inside the hourly ceiling.

    Enforced here rather than at the call sites so no caller can get it wrong:
    the audit and the crawl draw on the same allowance, and pacing each of them
    correctly on its own would still breach the limit together.
    """
    while True:
        stamps = _read_window()
        if len(stamps) < HOURLY_MAX:
            stamps.append(time.time())
            try:
                os.makedirs(os.path.dirname(_WINDOW_PATH), exist_ok=True)
                with open(_WINDOW_PATH, "w", encoding="utf-8") as fh:
                    json.dump(stamps, fh)
            except OSError:
                pass  # pacing is best-effort; never fail a fetch over bookkeeping
            return
        wait = 3600 - (time.time() - min(stamps)) + 1
        print(
            f"  hourly ceiling reached ({HOURLY_MAX}/h); waiting {wait / 60:.0f} min",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(max(1.0, wait))


UA = "ada-docket/0.1 (open dataset of ADA Title III filings; +https://github.com/)"

# Nature of suit codes queried.
#   446 — Civil Rights: Americans with Disabilities - Other  (where web cases land)
#   443 — Civil Rights: Accommodations
SUIT_NATURES = ("446", "443")

# 443 is NOT an ADA-only code. Clerks file Fair Housing Act, section 1983 and
# Title VII matters under it too, and publishing those under an "ADA Title III"
# heading would misstate what a named person was sued over. A 443 docket is only
# kept when its cause of action cites the ADA itself (42 U.S.C. 12101 et seq.).
# 446 is the ADA code by definition and is kept as it stands.
ADA_CAUSE = re.compile(r"\b42:12\d{3}\b")


def is_ada(row: dict) -> bool:
    nos = (row.get("suitNature") or "").strip()
    if nos.startswith("446"):
        return True
    return nos.startswith("443") and bool(ADA_CAUSE.search(row.get("cause") or ""))


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

# The record is partitioned by filing month, one file per month. A single
# combined file would be rewritten in full every day, and three years of daily
# rewrites of a multi-megabyte blob turns the git history into tens of
# gigabytes. Partitioned, only the current month's file changes each day and
# closed months never move again.

KEEP = (
    "docket_id",
    "caseName",
    "court",
    "court_id",
    "court_citation_string",
    "dateFiled",
    "docketNumber",
    "suitNature",
    "cause",
    "jurisdictionType",
    "docket_absolute_url",
    "party",
    "attorney",
    "firm",
    "assignedTo",
)


# Every HTTP call the process makes, counted. The daily ceiling of 125 is the
# scarcest resource this project has, and a backfill that guesses at what it
# spent will either stop short of the budget or overrun it. Both were observed:
# the overrun is what truncated April 2025.
REQUESTS = 0


def get(url: str, tries: int = 5) -> dict:
    """GET with backoff. Anonymous callers are rate-limited; be a good citizen."""
    global REQUESTS
    for attempt in range(tries):
        _await_slot()
        REQUESTS += 1
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                wait = 60 * (attempt + 1) if e.code == 429 else 5 * (attempt + 1)
                print(f"  HTTP {e.code}, retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError:
            if attempt < tries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def slim(row: dict) -> dict:
    """Keep the fields the site actually renders. Drops recap_documents, which is
    the bulk of the payload and is not used downstream."""
    out = {k: row.get(k) for k in KEEP}
    # Defendant = the last named party in the caption ("Smith v. Acme Corp").
    name = out.get("caseName") or ""
    out["defendant"] = name.split(" v. ")[-1].strip() if " v. " in name else ""
    out["plaintiff"] = name.split(" v. ")[0].strip() if " v. " in name else ""
    return out


def partition(row: dict) -> str:
    """Month a filing belongs to. Rows with no usable filing date go to a
    quarantine file rather than being silently dropped."""
    d = row.get("dateFiled") or ""
    return d[:7] if len(d) >= 7 and d[4] == "-" else "unknown"


# Files in data/ that hold filings. `save()` writes YYYY-MM.ndjson and, for a
# row with no usable filing date, unknown.ndjson — nothing else. Readers used to
# take any *.ndjson in the directory instead, which is how pulse.ndjson came to
# be read as dockets: the fetch asked a readings row for its docket_id and died,
# the site published regardless, and a record that promises to be daily quietly
# stopped being one. Moving that file out fixed the instance; matching the name
# on the way in is what closes the class.
_PARTITION = re.compile(r"^(\d{4}-\d{2}|unknown)\.ndjson$")


def is_partition(name: str) -> bool:
    return bool(_PARTITION.match(name))


def load() -> dict[int, dict]:
    seen: dict[int, dict] = {}
    if not os.path.isdir(DATA_DIR):
        return seen
    for name in sorted(os.listdir(DATA_DIR)):
        if not is_partition(name):
            continue
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                seen[row["docket_id"]] = row
    return seen


def save(rows: dict[int, dict]) -> None:
    """Rewrite only the month files that actually changed, so a daily run leaves
    closed months byte-identical and git records nothing for them."""
    os.makedirs(DATA_DIR, exist_ok=True)
    months: dict[str, list[dict]] = {}
    for row in rows.values():
        months.setdefault(partition(row), []).append(row)

    for month, batch in months.items():
        batch.sort(key=lambda r: (r.get("dateFiled") or "", r.get("docket_id") or 0))
        body = "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in batch
        )
        path = os.path.join(DATA_DIR, f"{month}.ndjson")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                if fh.read() == body:
                    continue
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp, path)
        print(f"  wrote {month}.ndjson ({len(batch)} filings)")


# Whether the last crawl ran out of pages allowed rather than out of results.
# The distinction is the difference between "this is the whole month" and "this
# is as much of the month as the budget bought", and nothing downstream can
# recover it after the fact — which is precisely how a truncated April came to
# be published as a complete one.
LAST_CRAWL_TRUNCATED = False


def crawl(since: str, until: str, max_pages: int) -> list[dict]:
    """Walk the cursor-paginated result set for one nature-of-suit code at a time.
    Splitting the query keeps each result set small enough to page reliably."""
    global LAST_CRAWL_TRUNCATED
    LAST_CRAWL_TRUNCATED = False
    found: list[dict] = []
    for nos in SUIT_NATURES:
        params = {
            "type": "r",
            "q": f"suitNature:({nos})",
            "filed_after": since,
            "filed_before": until,
            "order_by": "dateFiled desc",
        }
        url = API + "?" + urllib.parse.urlencode(params)
        pages = 0
        while url and pages < max_pages:
            data = get(url)
            batch = data.get("results", [])
            found.extend(batch)
            pages += 1
            print(
                f"  nos={nos} page {pages}: +{len(batch)} (total reported {data.get('count')})"
            )
            url = data.get("next")
            if url:
                time.sleep(PAGE_PAUSE)
        if url:
            # There were more pages and we stopped anyway.
            LAST_CRAWL_TRUNCATED = True
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--days",
        type=int,
        default=7,
        help="look-back window in days (default 7; the daily job "
        "overlaps so late-indexed dockets are still caught)",
    )
    ap.add_argument("--since", help="explicit YYYY-MM-DD start, overrides --days")
    ap.add_argument("--until", help="explicit YYYY-MM-DD end, defaults to today")
    ap.add_argument("--max-pages", type=int, default=40)
    args = ap.parse_args()

    today = dt.date.today()
    since = args.since or (today - dt.timedelta(days=args.days)).isoformat()
    until = args.until or today.isoformat()

    print(f"ada-docket: fetching filings {since} .. {until}")
    existing = load()
    print(f"  {len(existing)} cases already on disk")

    raw = crawl(since, until, args.max_pages)

    added = 0
    dropped = 0
    for row in raw:
        did = row.get("docket_id")
        if did is None:
            continue
        if not is_ada(row):
            dropped += 1
            continue
        rec = slim(row)
        if did not in existing:
            rec["first_seen"] = until
            added += 1
        else:
            rec["first_seen"] = existing[did].get("first_seen", until)
        existing[did] = rec

    save(existing)
    print(f"  {dropped} non-ADA dockets dropped from the 443 code")
    print(f"  +{added} new, {len(existing)} total in {DATA_DIR}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as exc:
        # A 429 that survives the backoff means the daily ceiling is spent, not
        # that anything is broken. Saying so in one line matters: this runs
        # unattended and lands in a log a person only skims. A traceback there
        # reads like a defect and teaches the reader to stop looking, which is
        # how a genuine failure gets missed later.
        if exc.code == 429:
            print(
                "CourtListener rate limit reached (5/min, 50/hour, 125/day for "
                "anonymous callers). Nothing was written; the next run picks up "
                "where this one stopped. An API token would lift this.",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"CourtListener returned HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        sys.exit(1)
