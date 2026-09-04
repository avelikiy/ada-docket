#!/usr/bin/env python3
"""Record what can actually be measured about this site, once a day.

The project set itself a kill threshold before launch — close it if, at ninety
days, it has fewer than fifty subscribers or fewer than a hundred and twenty
unique readers. That threshold was written without checking whether either
number is observable. One of them is not.

A static site on github.io produces no server logs, and GitHub publishes no
traffic figures for Pages. Unique readers are therefore unmeasurable from here
at zero cost, and no amount of wanting the number produces it. Saying so in the
data is the point of this script: a threshold that cannot be evaluated is not a
threshold, it is a way of postponing the decision.

What IS observable, free and without an account:

    subscribers   Feedly serves a public subscriber count for any feed it has
                  indexed, unauthenticated. It counts Feedly's users only, so it
                  is a floor on real subscribers, never the whole figure.
    stars,        github.com repository signals, public. Weak — the measured
    watchers,     lesson from cycle 3 is that GitHub is not a discovery channel —
    forks         but free and honest about what it is.
    repo views    GitHub's traffic API, fourteen-day window. Requires a token
                  with push rights; counts views of the REPOSITORY page, which
                  is not the site. Recorded, clearly labelled, never conflated
                  with site traffic.

Everything else — sessions, uniques, search impressions — needs either a server,
a paid analytics account, or a human to sign in to Google Search Console. All
three are gates this company does not currently have. The gap is recorded as
null rather than estimated.

Writes one line per day to data/pulse.ndjson, keyed on the date, so re-running
the script on the same day corrects that day rather than appending a duplicate.
Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
PULSE = os.path.join(DATA_DIR, "pulse.ndjson")

REPO = os.environ.get("REPO_SLUG", "avelikiy/ada-docket")
FEED = os.environ.get("FEED_URL", "https://avelikiy.github.io/ada-docket/feed.xml")

UA = "ada-docket-pulse/1.0 (+https://github.com/avelikiy/ada-docket)"
TIMEOUT = 20


def get_json(url: str, token: str = "") -> object | None:
    """Fetch and parse JSON. Returns None on any failure — a missing reading is
    recorded as missing, never as a zero. A zero and an unanswered request mean
    opposite things when you are deciding whether to close a project."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        print(f"  ! {url} -> {exc}", file=sys.stderr)
        return None


def gh_token() -> str:
    """Prefer an explicit token; fall back to whatever the gh CLI is holding.

    The traffic endpoint is the only reading here that needs credentials. When
    none are available the reading is skipped, which is why every caller has to
    tolerate a null.
    """
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        out = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def feedly_subscribers(feed_url: str) -> int | None:
    """Public, unauthenticated subscriber count for an indexed feed.

    Feedly answers an unknown feed with an empty list rather than an error, and
    an unindexed feed genuinely has no Feedly subscribers, so [] is read as a
    true zero. A transport failure stays None.
    """
    fid = urllib.parse.quote(f"feed/{feed_url}", safe="")
    data = get_json(f"https://cloud.feedly.com/v3/feeds/{fid}")
    if data is None:
        return None
    if isinstance(data, list):  # unknown feed: nobody subscribes
        return 0
    if isinstance(data, dict):
        n = data.get("subscribers")
        return int(n) if isinstance(n, (int, float)) else 0
    return None


def repo_signals(slug: str) -> dict:
    data = get_json(f"https://api.github.com/repos/{slug}")
    if not isinstance(data, dict):
        return {"stars": None, "watchers": None, "forks": None}
    return {
        "stars": data.get("stargazers_count"),
        "watchers": data.get("subscribers_count"),
        "forks": data.get("forks_count"),
    }


def repo_traffic(slug: str, token: str) -> dict:
    """Fourteen-day repository-page traffic. NOT site traffic — see the module
    docstring. Needs push rights; without them both figures stay null."""
    if not token:
        return {"repo_views_14d": None, "repo_uniques_14d": None}
    data = get_json(f"https://api.github.com/repos/{slug}/traffic/views", token)
    if not isinstance(data, dict):
        return {"repo_views_14d": None, "repo_uniques_14d": None}
    return {
        "repo_views_14d": data.get("count"),
        "repo_uniques_14d": data.get("uniques"),
    }


def corpus_size() -> dict:
    """How much record there is to be found — the supply side of discovery."""
    cases = 0
    for name in sorted(os.listdir(DATA_DIR)):
        if name.endswith(".ndjson") and name != "pulse.ndjson":
            with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
                cases += sum(1 for line in fh if line.strip())
    site = os.path.join(ROOT, "site")
    pages = 0
    for dirpath, _dirs, files in os.walk(site):
        pages += sum(1 for f in files if f.endswith(".html"))
    return {"cases": cases, "pages": pages}


def read_history() -> list[dict]:
    if not os.path.exists(PULSE):
        return []
    rows = []
    with open(PULSE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def write_history(rows: list[dict]) -> None:
    rows.sort(key=lambda r: r.get("date", ""))
    tmp = PULSE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, PULSE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default="", help="record under this date, not today")
    args = ap.parse_args()

    today = args.date or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    token = gh_token()

    print(f"pulse {today}")
    reading = {"date": today}
    reading["subscribers"] = feedly_subscribers(FEED)
    reading.update(repo_signals(REPO))
    reading.update(repo_traffic(REPO, token))
    reading.update(corpus_size())

    # Recorded explicitly so the shape of the gap is in the data itself, not
    # only in a comment somebody has to remember to read.
    reading["site_uniques"] = None
    reading["site_uniques_note"] = (
        "unmeasurable: GitHub Pages publishes no traffic data"
    )

    history = [r for r in read_history() if r.get("date") != today]
    history.append(reading)
    write_history(history)

    for key in (
        "subscribers",
        "stars",
        "watchers",
        "forks",
        "repo_views_14d",
        "repo_uniques_14d",
        "cases",
        "pages",
    ):
        value = reading.get(key)
        print(f"  {key:<17} {'—' if value is None else value}")
    print(f"  {'site_uniques':<17} — (unmeasurable without a server)")
    print(f"\n{len(history)} readings in {os.path.relpath(PULSE, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
