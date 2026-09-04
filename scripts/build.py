#!/usr/bin/env python3
"""Render the static site and the open-data files from the monthly partitions.

Outputs into site/:
    index.html            the record, newest first
    court/<id>.html       one page per district court
    month/<YYYY-MM>.html  one page per filing month
    style.css, filter.js  shared, so the pages stay small
    cases.csv/.json       every tracked filing
    feed.xml              RSS of the newest filings
    sitemap.xml, robots.txt

The per-court and per-month pages exist for a measured reason. A repository or a
single index page is not discoverable on its own; what reaches people is a
long-tail search query landing on the page that answers exactly it — "ADA
lawsuits filed in S.D. Fla.", "ADA Title III filings August 2026". One page per
answer.

Standard library only, no build step: GitHub Pages serves site/ as-is.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")

# Set by the workflow so the feed and sitemap carry absolute URLs.
BASE_URL = os.environ.get("SITE_URL", "").rstrip("/")

CL = "https://www.courtlistener.com"
REPO = os.environ.get("REPO_URL", "https://github.com/avelikiy/ada-docket").rstrip("/")

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Corporate suffixes dropped when grouping defendants, so "ACME CORP." and
# "Acme Corp, Inc." land on one row.
ORG_TAIL = re.compile(
    r"[\s,.]*\b(inc|llc|l\.l\.c|ltd|corp|corporation|co|company|lp|llp|plc|"
    r"pllc|pc|na|n\.a)\b\.?$",
    re.IGNORECASE,
)

TABLE_LIMIT = 400


# ---------------------------------------------------------------- data ----


def load() -> list[dict]:
    """Read every monthly partition in data/ into one list, newest first."""
    rows = []
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith(".ndjson"):
            continue
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    rows.sort(key=lambda r: r.get("dateFiled") or "", reverse=True)
    return rows


def longdate(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or "—"
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def monthname(ym: str) -> str:
    try:
        y, m = ym.split("-")
        return f"{MONTHS[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return ym


def titlecase(name: str) -> str:
    """Title-case a shouted name without capitalising after an apostrophe, so
    DILLARD'S reads Dillard's. Mixed-case names are the court's own; leave them."""
    if not name.isupper():
        return name
    return re.sub(
        r"[A-Za-z]+(?:['’][A-Za-z]+)*",
        lambda m: m.group(0)[0].upper() + m.group(0)[1:],
        name.lower(),
    )


def normalise_org(name: str) -> str:
    prev = None
    out = (name or "").strip().strip(",.")
    while out != prev:
        prev = out
        out = ORG_TAIL.sub("", out).strip().strip(",.")
    return out.upper() or (name or "").upper()


def cause_cite(row: dict) -> str:
    """The statute cite out of the clerk's cause string, e.g. "42:12182" from
    "42:12182 Americans with Disabilities Act". Shown so a reader can see on what
    basis a filing is called an ADA matter rather than taking our word."""
    m = re.match(r"\s*([0-9]+:[0-9]+)", row.get("cause") or "")
    return m.group(1) if m else (row.get("cause") or "—")[:12]


def court_of(row: dict) -> str:
    return row.get("court_citation_string") or row.get("court") or "—"


def weekly(rows: list[dict], weeks: int = 26) -> list[tuple[dt.date, int]]:
    """Filings per week, oldest first. The current partial week is dropped: a
    half-counted bar reads as a collapse in filings, which would be a lie."""
    today = dt.date.today()
    this_monday = today - dt.timedelta(days=today.weekday())
    buckets: collections.Counter = collections.Counter()
    for r in rows:
        try:
            d = dt.date.fromisoformat(r["dateFiled"])
        except (TypeError, ValueError, KeyError):
            continue
        buckets[d - dt.timedelta(days=d.weekday())] += 1
    out = []
    for i in range(weeks, 0, -1):
        monday = this_monday - dt.timedelta(weeks=i)
        out.append((monday, buckets.get(monday, 0)))
    # Trim leading empty weeks. Before the record starts an empty bar would read
    # as "no lawsuits that week" when it means "not collected yet".
    while len(out) > 4 and out[0][1] == 0:
        out.pop(0)
    return out


# ------------------------------------------------------------ fragments ----


def caption_block(row: dict) -> str:
    """The hero: a filing set the way its own court sets a caption."""
    plaintiff = (row.get("plaintiff") or "").upper() or "PLAINTIFF"
    defendant = (row.get("defendant") or "").upper() or "DEFENDANT"
    return f"""
      <div class="caption" role="figure" aria-label="Most recent tracked filing">
        <div class="caption-parties">
          <p class="party">{html.escape(plaintiff)},</p>
          <p class="role">Plaintiff,</p>
          <p class="versus">v.</p>
          <p class="party">{html.escape(defendant)},</p>
          <p class="role">Defendant.</p>
        </div>
        <div class="caption-rail" aria-hidden="true"></div>
        <div class="caption-meta">
          <p class="docket-no">{html.escape(row.get("docketNumber") or "")}</p>
          <p>{html.escape(court_of(row))}</p>
          <p>Filed {longdate(row.get("dateFiled") or "")}</p>
        </div>
      </div>"""


def bar_strip(series: list[tuple[dt.date, int]]) -> str:
    peak = max((n for _, n in series), default=1) or 1
    bars = []
    for monday, n in series:
        label = f"Week of {longdate(monday.isoformat())}: {n} filings"
        bars.append(
            f'<div class="bar" style="--h:{round(100 * n / peak, 1)}%" '
            f'title="{html.escape(label)}">'
            f'<span class="sr-only">{html.escape(label)}</span></div>'
        )
    first = series[0][0] if series else dt.date.today()
    last = series[-1][0] if series else dt.date.today()
    return f"""
      <figure class="trend">
        <div class="bars" role="img" aria-label="Weekly filing counts, {longdate(first.isoformat())} to {longdate(last.isoformat())}">
          {"".join(bars)}
        </div>
        <figcaption>
          <span>{longdate(first.isoformat())}</span>
          <span>Peak week: {peak} filings</span>
          <span>{longdate(last.isoformat())}</span>
        </figcaption>
      </figure>"""


def table(
    rows: list[dict], depth: str, limit: int = TABLE_LIMIT, show_court: bool = True
) -> str:
    today = dt.date.today()
    fresh = (today - dt.timedelta(days=3)).isoformat()
    body = []
    for r in rows[:limit]:
        url = CL + (r.get("docket_absolute_url") or "")
        new = (r.get("dateFiled") or "") >= fresh
        defendant = r.get("defendant") or r.get("caseName") or "—"
        hay = " ".join(
            filter(
                None,
                [r.get("caseName"), r.get("court"), court_of(r), r.get("docketNumber")],
            )
        ).lower()
        court_cell = (
            f'<td class="c-court"><a href="{depth}court/'
            f'{html.escape(r.get("court_id") or "unknown")}.html">'
            f"{html.escape(court_of(r))}</a></td>"
            if show_court
            else ""
        )
        body.append(f"""
          <tr data-search="{html.escape(hay)}">
            <td class="c-date"><time datetime="{html.escape(r.get("dateFiled") or "")}">{html.escape(r.get("dateFiled") or "—")}</time>{' <b class="new">new</b>' if new else ""}</td>
            <td class="c-def"><a href="{html.escape(url)}" rel="noopener">{html.escape(defendant)}</a></td>
            <td class="c-plaintiff">{html.escape(r.get("plaintiff") or "—")}</td>
            {court_cell}
            <td class="c-no">{html.escape(r.get("docketNumber") or "—")}</td>
            <td class="c-cause" title="{html.escape((r.get("cause") or "") + " · nature of suit " + (r.get("suitNature") or ""))}">{html.escape(cause_cite(r))}</td>
          </tr>""")
    head_court = '<th scope="col">Court</th>' if show_court else ""
    return f"""
      <div class="filter">
        <label for="q">Search defendant, court or docket number</label>
        <input id="q" type="search" autocomplete="off" placeholder="Marriott, S.D. Fla., 1:26-cv">
        <output id="count" for="q"></output>
      </div>
      <div class="scroller">
        <table>
          <thead><tr><th scope="col">Filed</th><th scope="col">Defendant</th><th scope="col">Plaintiff</th>{head_court}<th scope="col">Docket</th><th scope="col">Cause</th></tr></thead>
          <tbody id="rows">{"".join(body)}</tbody>
        </table>
      </div>"""


def leaderboard(items, head: str, note: str, href: str = "") -> str:
    """items is [(label, n)] or [((label, slug), n)] when the rows should link."""
    peak = items[0][1] if items else 1
    lis = []
    for key, n in items:
        label, link = key if isinstance(key, tuple) else (key, None)
        shown = html.escape(titlecase(label))
        if href and link:
            shown = f'<a href="{html.escape(href + link)}">{shown}</a>'
        lis.append(f"""
            <li>
              <span class="lb-name">{shown}</span>
              <span class="lb-bar" style="--w:{round(100 * n / peak, 1)}%" aria-hidden="true"></span>
              <span class="lb-n">{n}</span>
            </li>""")
    return f"""
      <section class="board">
        <h3>{html.escape(head)}</h3>
        <ol class="lb">{"".join(lis)}</ol>
        <p class="note">{note}</p>
      </section>"""


# ---------------------------------------------------------------- shell ----

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'"
    "%3E%3Crect width='16' height='16' fill='%23eaebe5'/%3E%3Cpath d='M5 2v12M9 3.2q2"
    " 4.8 0 9.6' stroke='%23131a26' stroke-width='1.4' fill='none'/%3E%3C/svg%3E"
)

DISCLAIMER = """This is a mirror of federal court dockets, published for research. Case
       type — including whether a filing is an ADA Title&nbsp;III lawsuit — is our best
       reading of the court's own nature-of-suit and cause codes, which courts
       themselves code inconsistently; verify the actual claim on the docket before
       treating any entry as an ADA matter. A filing shown here may since have been
       dismissed, settled or otherwise resolved: this record shows what was filed, not
       current case status.</p>
    <p>This is not legal advice, not a consumer report under the Fair Credit Reporting
       Act, and not a credit, insurance, employment, tenancy or background-screening
       product. Do not use it, or let a tool built on it be used, to make a decision
       about any individual's or business's eligibility for anything. Court records
       contain errors — verify against the linked docket before relying on anything
       here."""


def page(
    *,
    title: str,
    description: str,
    depth: str,
    heading: str,
    standfirst: str,
    body: str,
    crumb: str = "",
    canonical: str = "",
) -> str:
    """One shell for every page. depth is "" at the root, "../" one level down."""
    generated = dt.datetime.now(dt.timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    link_canonical = (
        f'\n<link rel="canonical" href="{html.escape(BASE_URL + "/" + canonical)}">'
        if BASE_URL and canonical
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="{depth}style.css">
<link rel="alternate" type="application/rss+xml" title="ADA Title III filings" href="{depth}feed.xml">{link_canonical}
</head>
<body>

<header>
  <div class="wrap">
    <div class="masthead">
      <h1><a href="{depth}index.html">ADA Title&nbsp;III filings</a></h1>
      <p>Every federal disability-access lawsuit as it reaches the public docket.
         Read the record, take the data, no account.</p>
    </div>
  </div>
</header>

<main>
  <div class="wrap">
    {f'<nav class="crumb" aria-label="Breadcrumb">{crumb}</nav>' if crumb else ""}
    <div class="page-head">
      <h2 class="page-title">{heading}</h2>
      <p class="standfirst">{standfirst}</p>
    </div>
  </div>
  {body}
</main>

<footer>
  <div class="wrap">
    <p>Rebuilt {generated}. Dockets from
       <a href="https://www.courtlistener.com" rel="noopener">CourtListener</a>,
       a service of the Free Law Project, who neither produced nor endorsed this
       page. Compilation released under CC0.</p>
    <p>{DISCLAIMER}</p>
    <p><a href="{depth}index.html">The whole record</a> ·
       <a href="{depth}cases.csv">CSV</a> ·
       <a href="{depth}cases.json">JSON</a> ·
       <a href="{depth}feed.xml">RSS</a> ·
       <a href="{depth}pulse.html">Pulse</a></p>
  </div>
</footer>

<script src="{depth}filter.js" defer></script>
</body>
</html>
"""


# ----------------------------------------------------------------- pages ----


def index_page(rows: list[dict]) -> str:
    today = dt.date.today()
    last7 = [
        r
        for r in rows
        if (r.get("dateFiled") or "") >= (today - dt.timedelta(days=7)).isoformat()
    ]
    last30 = [
        r
        for r in rows
        if (r.get("dateFiled") or "") >= (today - dt.timedelta(days=30)).isoformat()
    ]
    dates = [r["dateFiled"] for r in rows if r.get("dateFiled")]
    earliest, latest = (min(dates), max(dates)) if dates else ("", "")

    courts = collections.Counter(
        (court_of(r), r.get("court_id") or "unknown") for r in rows
    )
    court_items = [
        ((label, f"{cid}.html"), n) for (label, cid), n in courts.most_common(10)
    ]

    # Counsel of record on filings under 30 days old. On a freshly opened docket
    # the appearances are overwhelmingly plaintiff-side; defence counsel has not
    # entered yet. Older dockets mix both sides, so they are excluded here.
    firms: collections.Counter = collections.Counter()
    for r in last30:
        for f in r.get("firm") or []:
            if f and len(f) > 3:
                firms[f.strip()] += 1

    months = sorted(
        {(r.get("dateFiled") or "")[:7] for r in rows if r.get("dateFiled")},
        reverse=True,
    )
    month_links = " · ".join(
        f'<a href="month/{m}.html">{monthname(m)}</a>' for m in months
    )

    boards = [
        leaderboard(
            court_items,
            "Where the filings land",
            "District courts by tracked filing count. Each opens that court's record.",
            href="court/",
        ),
        leaderboard(
            firms.most_common(8),
            "Counsel on new filings",
            "Firms appearing on dockets opened in the last 30 days. On a new docket "
            "the appearances are almost entirely plaintiff-side — defence counsel "
            "has not entered yet.",
        ),
    ]
    body = f"""
  <div class="wrap">
    <div class="hero">
      {caption_block(rows[0]) if rows else "<p>No filings tracked yet.</p>"}
      <p class="hero-note">The most recent filing in the record, set the way its own court sets it.</p>
    </div>

    <div class="stats">
      <div class="stat"><b>{len(rows):,}</b><span>filings tracked</span></div>
      <div class="stat"><b>{len(last7):,}</b><span>in the last seven days</span></div>
      <div class="stat"><b>{round(len(last30) / 30, 1)}</b><span>a day, past month</span></div>
      <div class="stat"><b>{len(courts):,}</b><span>district courts</span></div>
    </div>

    <section>
      <h2>Filings a week</h2>
      <p>Complete weeks only. The four most recent are marked; the current week is
         still open and is not shown.</p>
      {bar_strip(weekly(rows))}
    </section>

    <section>
      <h2>Who is filing, and where</h2>
      <p>Read these as counts in this record, not as national totals.</p>
      <div class="boards">{"".join(boards)}</div>
    </section>

    <section>
      <h2>The record</h2>
      <p>Newest first. Every defendant links to the docket on CourtListener, where
         the filings themselves live. By month: {month_links}</p>
      {table(rows, depth="")}
      <p class="note">Showing the {min(len(rows), TABLE_LIMIT):,} most recent of
         {len(rows):,} tracked filings. The downloads carry all of them.</p>
    </section>
  </div>

  <div class="method">
    <div class="wrap">
      <section>
        <h2>How this is made, and where it falls short</h2>
        <div class="cols">
          <div>
            <h3>Where the data comes from</h3>
            <p>Federal civil dockets, read once a day from the CourtListener RECAP
               search API and kept as they were published. Nothing here is inferred:
               every field is the court's own.</p>
            <p>A filing enters when its docket carries nature of suit <b>446</b>
               (Americans with Disabilities&nbsp;— Other) or <b>443</b>
               (Accommodations). That is the coding the ADA Title&nbsp;III bar uses,
               web-access cases included.</p>
          </div>
          <div>
            <h3>This record is a floor, not a census</h3>
            <p>Free PACER metadata does not carry a nature-of-suit code until someone
               buys the docket, so a filing only becomes visible here once it has been
               purchased into RECAP. Compared against the published annual counts, a
               record built this way lands near two-thirds of federal ADA
               Title&nbsp;III filings — not all of them.</p>
            <p>State-court actions and demand letters that never become suits are
               invisible entirely, and most access disputes end in a letter. Treat
               every count here as a lower bound.</p>
          </div>
          <div>
            <h3>What a caption cannot tell you</h3>
            <p>Defendant and plaintiff are read from the case caption. A caption names
               parties, not websites, and does not say what the claim was about — the
               446 code covers every kind of access claim, of which web accessibility
               is one part.</p>
            <ul class="downloads">
              <li><a href="cases.csv">cases.csv</a> — every tracked filing</li>
              <li><a href="cases.json">cases.json</a> — the same, machine-readable</li>
              <li><a href="feed.xml">feed.xml</a> — RSS, newest fifty</li>
            </ul>
            <p class="note">Record spans {longdate(earliest)} to {longdate(latest)}.
               Public record, published under CC0.</p>
          </div>
          <div>
            <h3>Corrections and removal</h3>
            <p>We publish what the federal docket says. If we got one wrong — the wrong
               party as plaintiff or defendant, the wrong court, the wrong case type, or
               a case shown here that was later dismissed, settled or sealed — tell us.
               We check it against the source docket and correct the entry, and we aim
               to resolve verified corrections within five business days.</p>
            <p>We do not remove a filing because a party would prefer it not be public.
               It already is public, on the court's own docket, and removing it here
               would misrepresent the record rather than fix it. We do correct factual
               errors, update case status, and take an entry down when the underlying
               record is sealed, expunged or vacated by the court.</p>
            <p class="note">To report an error,
               <a href="{REPO}/issues/new" rel="noopener">open an issue</a> with the
               docket number and what is wrong. Issues are public — send nothing you
               would not want read.</p>
          </div>
        </div>
      </section>
    </div>
  </div>"""

    return page(
        title="ADA Title III filings — a daily record of federal accessibility lawsuits",
        description=(
            "Every federal Americans with Disabilities Act Title III lawsuit as it "
            "reaches the docket, updated daily. Defendants, courts, docket numbers. "
            "Free CSV, JSON and RSS, no account."
        ),
        depth="",
        canonical="",
        heading="The federal access docket, every day",
        standfirst=(
            f"{len(rows):,} filings tracked across {len(courts)} district courts, "
            f"{longdate(earliest)} to {longdate(latest)}."
        ),
        body=body,
    )


def court_page(court_id: str, rows: list[dict]) -> str:
    label = court_of(rows[0])
    full = rows[0].get("court") or label
    dates = sorted(r["dateFiled"] for r in rows if r.get("dateFiled"))
    span = f"{longdate(dates[0])} to {longdate(dates[-1])}" if dates else "—"
    firms: collections.Counter = collections.Counter()
    for r in rows:
        for f in r.get("firm") or []:
            if f and len(f) > 3:
                firms[f.strip()] += 1
    body = f"""
  <div class="wrap">
    <div class="stats">
      <div class="stat"><b>{len(rows):,}</b><span>filings tracked here</span></div>
      <div class="stat"><b>{len(firms):,}</b><span>firms of record</span></div>
      <div class="stat"><b>{len({r.get("plaintiff") for r in rows}):,}</b><span>named plaintiffs</span></div>
    </div>
    <section>
      <h2>Filings a week in {html.escape(label)}</h2>
      <p>Complete weeks only.</p>
      {bar_strip(weekly(rows))}
    </section>
    <section>
      <h2>Counsel of record</h2>
      <p>Across every filing tracked in this district, both sides included.</p>
      <div class="boards">{leaderboard(firms.most_common(10), "Firms appearing most often", "Counted once per docket.")}</div>
    </section>
    <section>
      <h2>The record for {html.escape(label)}</h2>
      <p>Newest first. Each defendant links to the docket on CourtListener.</p>
      {table(rows, depth="../", show_court=False)}
      <p class="note">Showing the {min(len(rows), TABLE_LIMIT):,} most recent of {len(rows):,}.
         The <a href="../cases.csv">CSV</a> carries every district, and the
         <a href="../index.html">method note</a> explains what this record misses.</p>
    </section>
  </div>"""
    return page(
        title=f"ADA Title III lawsuits filed in {label} — the full record",
        description=(
            f"Every Americans with Disabilities Act Title III lawsuit tracked in the "
            f"{full}, {span}. {len(rows):,} filings with defendants, docket numbers "
            f"and counsel. Updated daily, free to download."
        ),
        depth="../",
        canonical=f"court/{court_id}.html",
        crumb='<a href="../index.html">The record</a> → ' + html.escape(label),
        heading=f"ADA Title III filings in {html.escape(label)}",
        standfirst=f"{len(rows):,} filings on this record, {span}.",
        body=body,
    )


def load_pulse() -> list[dict]:
    """Daily readings written by scripts/pulse.py, oldest first."""
    path = os.path.join(DATA_DIR, "pulse.ndjson")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    out.sort(key=lambda r: r.get("date", ""))
    return out


# What the ledger shows, and — the point of the page — what it cannot.
# (key, label, how it is read, gloss). A key of None is a line we promised
# ourselves we would watch and then found we had no way to see.
LEDGER = [
    (
        "subscribers",
        "Feed subscribers",
        "Feedly's public count for this feed, no account needed.",
        "Counts Feedly's readers only, so the real figure is this or higher, "
        "never lower.",
    ),
    (
        "stars",
        "Repository stars",
        "github.com, public.",
        "Kept for completeness. We measured in cycle three that GitHub is not a "
        "discovery channel, and nothing here is expected to move.",
    ),
    (
        "repo_uniques_14d",
        "Repository visitors",
        "GitHub's traffic API, rolling fourteen days.",
        "Visitors to the repository page. Not readers of this site — GitHub "
        "reports nothing about Pages traffic.",
    ),
    (
        None,
        "Readers of this site",
        "Nothing reports it.",
        "A static site on github.io writes no logs, and GitHub publishes no "
        "traffic figures for Pages. Measuring it would take a server, a paid "
        "analytics account, or a Search Console sign-in. This project has none "
        "of the three, so the line stays empty rather than guessed at.",
    ),
    (
        None,
        "Search impressions",
        "Nothing reports it.",
        "Same gap. Search Console would answer it and needs a person to verify "
        "the property once.",
    ),
]


def pulse_page(rows: list[dict], readings: list[dict]) -> str:
    """The project's own scoreboard, including the half of it we cannot see.

    This project set a closing condition before it launched — fewer than fifty
    subscribers or fewer than a hundred and twenty unique readers at ninety days
    and it shuts down — and only afterwards checked whether either number could
    be read. One cannot. Publishing that, rather than quietly redefining the
    threshold later, is the whole reason this page exists.
    """
    latest = readings[-1] if readings else {}
    first = readings[0] if readings else {}

    def shown(key: str) -> str:
        value = latest.get(key)
        return "—" if value is None else f"{value:,}"

    started = first.get("date") or dt.date.today().isoformat()
    day = 0
    try:
        day = (dt.date.today() - dt.date.fromisoformat(started)).days
    except ValueError:
        pass

    def entry(key, name, how, gloss) -> str:
        # A readable line carries its figure. An unreadable one carries ruled
        # blank paper, which states the gap before the sentence under it does.
        value = (
            f'<p class="led-value">{shown(key)}</p>'
            if key
            else '<p class="led-value led-void"><span class="sr-only">no reading</span></p>'
        )
        return f"""      <div class="led{"" if key else " led-blank"}">
        <p class="led-name">{html.escape(name)}</p>
        {value}
        <p class="led-how">{html.escape(how)}</p>
        <p class="led-gloss">{html.escape(gloss)}</p>
      </div>"""

    observed = "\n".join(entry(*e) for e in LEDGER if e[0])
    unobserved = "\n".join(entry(*e) for e in LEDGER if not e[0])

    history = ""
    if readings:
        head = "".join(
            f"<th>{html.escape(label)}</th>"
            for label in (
                "Date",
                "Subscribers",
                "Stars",
                "Repo visitors",
                "Filings",
                "Pages",
            )
        )
        body_rows = "\n".join(
            f'<tr><td class="c-date">{html.escape(r.get("date", ""))}</td>'
            + "".join(
                f'<td class="c-no">{"—" if r.get(k) is None else format(r[k], ",")}</td>'
                for k in ("subscribers", "stars", "repo_uniques_14d", "cases", "pages")
            )
            + "</tr>"
            for r in reversed(readings)
        )
        history = f"""
  <section class="wrap">
    <h2>Every reading</h2>
    <p>One row a day, written by the same job that fetches the filings. The
       record of what we watched is public for the same reason the filings
       are.</p>
    <div class="scroller">
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>
{body_rows}
        </tbody>
      </table>
    </div>
    <p class="note">Raw readings: <a href="pulse.ndjson">pulse.ndjson</a>.</p>
  </section>"""

    body = f"""
  <section class="wrap">
    <div class="stats">
      <div class="stat"><b>{shown("subscribers")}</b><span>feed subscribers</span></div>
      <div class="stat"><b>—</b><span>readers of this site</span></div>
      <div class="stat"><b>{day}</b><span>days since the first reading</span></div>
      <div class="stat"><b>{len(rows):,}</b><span>filings on the record</span></div>
    </div>
  </section>

  <section class="wrap">
    <h2>The closing condition</h2>
    <p>Fewer than fifty subscribers, or fewer than a hundred and twenty unique
       readers, ninety days after launch, and this project closes. That was
       written down before launch so it could not be softened afterwards to suit
       whatever the numbers turned out to be.</p>
    <p>Half of it cannot be evaluated. Unique readers are not observable from a
       static site at no cost, which we established only after setting the
       condition. The subscriber half stands and is read below. The reader half
       is void, and calling it void is more useful than substituting a number
       that looks like it but is not.</p>
  </section>

  <section class="wrap">
    <h2>What is observed</h2>
    <p>Each of these is free, needs no account, and is recorded once a day by
       the same job that fetches the filings.</p>
    <div class="ledger">
{observed}
    </div>
  </section>

  <section class="wrap">
    <h2>What nothing reports</h2>
    <p>These are the figures the project wanted and cannot have. They are ruled
       and left blank rather than filled with a proxy, because a proxy in this
       column is how a closing condition quietly stops meaning anything.</p>
    <div class="ledger ledger-void">
{unobserved}
    </div>
  </section>
{history}
"""
    return page(
        title="Pulse — how this record is doing, and what it cannot see",
        description=(
            "Daily readings for the ADA Title III filings record: feed "
            "subscribers, repository signals, corpus size — and an explicit "
            "account of the figures a static site cannot measure."
        ),
        depth="",
        heading="Pulse",
        standfirst=(
            "What this project can measure about itself, what it cannot, and the "
            "condition under which it closes."
        ),
        crumb='<a href="index.html">The record</a> · Pulse',
        canonical="pulse.html",
        body=body,
    )


def month_page(ym: str, rows: list[dict], order: list[str]) -> str:
    courts = collections.Counter(
        (court_of(r), r.get("court_id") or "unknown") for r in rows
    )
    court_items = [
        ((label, f"{cid}.html"), n) for (label, cid), n in courts.most_common(10)
    ]
    i = order.index(ym)
    prev_link = (
        f'<a href="{order[i - 1]}.html">← {monthname(order[i - 1])}</a>'
        if i > 0
        else ""
    )
    next_link = (
        f'<a href="{order[i + 1]}.html">{monthname(order[i + 1])} →</a>'
        if i < len(order) - 1
        else ""
    )
    body = f"""
  <div class="wrap">
    <div class="stats">
      <div class="stat"><b>{len(rows):,}</b><span>filings this month</span></div>
      <div class="stat"><b>{len(courts):,}</b><span>district courts</span></div>
      <div class="stat"><b>{round(len(rows) / 30, 1)}</b><span>a day</span></div>
    </div>
    <section>
      <h2>Where they landed</h2>
      <p>District courts by filings recorded in {monthname(ym)}.</p>
      <div class="boards">{leaderboard(court_items, "Courts this month", "Each opens that court's full record.", href="../court/")}</div>
    </section>
    <section>
      <h2>Every filing in {monthname(ym)}</h2>
      <p>Newest first. Each defendant links to the docket on CourtListener.</p>
      {table(rows, depth="../", limit=len(rows))}
    </section>
    <nav class="pager">{prev_link}{next_link}</nav>
  </div>"""
    return page(
        title=f"ADA Title III lawsuits filed in {monthname(ym)}",
        description=(
            f"The {len(rows):,} federal Americans with Disabilities Act Title III "
            f"lawsuits tracked for {monthname(ym)}, across {len(courts)} district "
            f"courts. Defendants, courts and docket numbers, free to download."
        ),
        depth="../",
        canonical=f"month/{ym}.html",
        crumb='<a href="../index.html">The record</a> → ' + monthname(ym),
        heading=f"Filings in {monthname(ym)}",
        standfirst=f"{len(rows):,} filings across {len(courts)} district courts.",
        body=body,
    )


# --------------------------------------------------------------- assets ----

STYLE = """/* ADA Title III filings — one stylesheet for every page.
   Set in the vernacular of a federal pleading: schoolbook serif, pleading-paper
   ground, court-stamp oxblood, seal blue. */
:root {
  --paper:#eaebe5; --paper-2:#f2f2ee; --ink:#131a26; --ink-soft:#4a5260;
  --rule:#b9bcb2; --stamp:#7a2e2e; --seal:#2f4a6b;
  --serif:"Century Schoolbook","New Century Schoolbook","Century Schoolbook L",Georgia,"Times New Roman",serif;
  --mono:"SFMono-Regular",Menlo,Consolas,"Liberation Mono",monospace;
}
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--paper); color:var(--ink);
       font-family:var(--serif); font-size:17px; line-height:1.55; }
.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px;
           overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0; }
a { color:var(--seal); text-decoration-thickness:1px; text-underline-offset:2px; }
a:hover { color:var(--stamp); }
:focus-visible { outline:2px solid var(--stamp); outline-offset:2px; }
.wrap { max-width:70rem; margin:0 auto; padding:0 1.5rem; }

header { border-bottom:1px solid var(--ink); }
.masthead { display:flex; flex-wrap:wrap; align-items:baseline; gap:.75rem 1.5rem;
            padding:2.25rem 0 1rem; }
h1 { font-size:clamp(1.7rem,3.6vw,2.4rem); line-height:1.1; margin:0; font-weight:400;
     letter-spacing:-.01em; }
h1 a { color:inherit; text-decoration:none; }
.masthead p { margin:0; color:var(--ink-soft); max-width:32rem; font-size:.95rem; }

.crumb { padding:1.25rem 0 0; font-size:.9rem; color:var(--ink-soft); }
.page-head { padding:1.5rem 0 0; }
.page-title { font-size:clamp(1.5rem,3vw,2rem); font-weight:400; margin:0 0 .3rem; }
.standfirst { margin:0; color:var(--ink-soft); max-width:44rem; }

.hero { padding:2.5rem 0 2rem; border-bottom:1px solid var(--rule); }
.caption { display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);
           gap:0 1.75rem; max-width:46rem; margin:0 auto; background:var(--paper-2);
           border:1px solid var(--rule); padding:2rem 2rem 1.75rem; }
.caption p { margin:0; }
.caption-parties { min-width:0; }
.party { font-size:1.05rem; letter-spacing:.02em; overflow-wrap:anywhere; }
.role { padding-left:2.5rem; font-style:italic; color:var(--ink-soft); }
.versus { padding-left:1.25rem; margin:.35rem 0 !important; }
/* The paren column of a federal caption runs unbroken from the first party to
   the last. Drawn absolutely so it fills the parties' height and adds none. */
.caption-rail { position:relative; width:1ch; }
.caption-rail::before {
  content:")\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)\\A)";
  position:absolute; inset:0; overflow:hidden; white-space:pre;
  color:var(--rule); font-size:1.05rem; line-height:1.3; user-select:none;
}
.caption-meta { min-width:0; }
.caption-meta p { color:var(--ink-soft); }
.docket-no { font-family:var(--mono); font-size:.95rem; color:var(--ink) !important;
             letter-spacing:-.02em; margin-bottom:.35rem !important; }
.hero-note { max-width:46rem; margin:1rem auto 0; color:var(--ink-soft); font-size:.95rem; }

.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));
         margin-top:2rem; border-top:1px solid var(--rule);
         border-bottom:1px solid var(--ink); }
.hero + .stats { margin-top:0; }
.stat { padding:1.25rem 0; }
.stat + .stat { border-left:1px solid var(--rule); padding-left:1.25rem; }
.stat b { display:block; font-family:var(--mono); font-size:1.6rem; font-weight:400;
          letter-spacing:-.03em; }
.stat span { color:var(--ink-soft); font-size:.9rem; }

section { padding:2.5rem 0; }
h2 { font-size:1.35rem; font-weight:400; margin:0 0 .35rem; }
h2 + p { margin:0 0 1.5rem; color:var(--ink-soft); max-width:46rem; }
h3 { font-size:1rem; font-weight:400; margin:0 0 .9rem; padding-bottom:.4rem;
     border-bottom:1px solid var(--rule); }

.trend { margin:0; }
.bars { display:flex; align-items:flex-end; gap:2px; height:9rem;
        border-bottom:1px solid var(--ink); }
.bar { flex:1; height:var(--h); min-height:1px; background:var(--seal); }
.bar:nth-last-child(-n+4) { background:var(--stamp); }
.trend figcaption { display:flex; justify-content:space-between; gap:1rem;
                    margin-top:.5rem; color:var(--ink-soft); font-size:.85rem; }

.boards { display:grid; grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));
          gap:2rem 2.5rem; }
.board { max-width:36rem; }
.lb { list-style:none; margin:0; padding:0; }
.lb li { display:grid; grid-template-columns:1fr 4.5rem 2.5rem; align-items:center;
         gap:.75rem; padding:.4rem 0; border-bottom:1px solid rgba(185,188,178,.5); }
.lb-name { font-size:.95rem; overflow-wrap:anywhere; }
.lb-bar { height:6px; background:var(--seal); width:var(--w); justify-self:start; }
.lb-n { font-family:var(--mono); font-size:.85rem; text-align:right; color:var(--ink-soft); }
.note { font-size:.82rem; color:var(--ink-soft); margin:.75rem 0 0; }

.filter { display:flex; flex-wrap:wrap; gap:.75rem; align-items:baseline;
          margin-bottom:1rem; }
.filter input { font:inherit; font-size:.95rem; padding:.5rem .7rem;
                min-width:min(22rem,100%); background:var(--paper-2);
                border:1px solid var(--rule); color:inherit; }
.filter output { color:var(--ink-soft); font-size:.9rem; }
.scroller { overflow-x:auto; border-top:1px solid var(--ink); }
table { width:100%; border-collapse:collapse; font-size:.95rem; }
th { text-align:left; font-weight:400; font-style:italic; color:var(--ink-soft);
     padding:.6rem .9rem .6rem 0; border-bottom:1px solid var(--rule); white-space:nowrap; }
td { padding:.55rem .9rem .55rem 0; border-bottom:1px solid rgba(185,188,178,.45);
     vertical-align:top; }
tbody tr:hover { background:var(--paper-2); }
.c-date, .c-no, .c-cause { font-family:var(--mono); font-size:.85rem; white-space:nowrap;
                           color:var(--ink-soft); }
.c-cause { cursor:help; }
.c-def { min-width:14rem; }
.c-plaintiff, .c-court { color:var(--ink-soft); white-space:nowrap; }
.new { color:var(--stamp); font-weight:400; font-style:italic;
       font-family:var(--serif); font-size:.8rem; }
tr[hidden] { display:none; }

.pager { display:flex; justify-content:space-between; gap:1rem; padding:0 0 3rem; }
.pager a:only-child { margin-left:auto; }

.method { border-top:1px solid var(--ink); }
.cols { display:grid; grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));
        gap:2rem 2.5rem; }
.cols p { margin:0 0 .8rem; font-size:.95rem; }
.downloads { list-style:none; padding:0; margin:.5rem 0 0; }
.downloads li { padding:.35rem 0; border-bottom:1px solid rgba(185,188,178,.5);
                font-size:.95rem; }
/* The pulse ledger. Entries we can read are written on the line; entries
   nothing reports are left as ruled paper with nothing on it, which says the
   thing faster than the sentence underneath does. */
.ledger { display:grid; grid-template-columns:repeat(auto-fit,minmax(19rem,1fr));
          gap:0 2.5rem; border-top:1px solid var(--ink); }
.led { padding:1.1rem 0 1.2rem; border-bottom:1px solid var(--rule); }
.led p { margin:0; }
.led-name { font-size:1rem; }
.led-value { font-family:var(--mono); font-size:1.55rem; letter-spacing:-.03em;
             color:var(--seal); margin:.15rem 0 .5rem !important; }
.led-how { font-style:italic; color:var(--ink-soft); font-size:.9rem;
           margin-bottom:.35rem !important; }
.led-gloss { color:var(--ink-soft); font-size:.85rem; max-width:34rem; }
.ledger-void { grid-template-columns:repeat(auto-fit,minmax(22rem,1fr)); }
/* Four ruled lines with nothing written on them. The blank is the statement;
   the paragraph underneath only explains it. */
.led-void { height:4.6rem; margin:.35rem 0 .75rem !important;
  background:repeating-linear-gradient(
    to bottom, transparent 0 1.09rem, var(--rule) 1.09rem 1.15rem); }

footer { border-top:1px solid var(--ink); padding:1.5rem 0 3rem; color:var(--ink-soft);
         font-size:.85rem; }
footer p { margin:0 0 .4rem; max-width:46rem; }

@media (max-width:44rem) {
  .caption { grid-template-columns:1fr; gap:1.25rem; padding:1.5rem; }
  .caption-rail { display:none; }
  .caption-meta { border-top:1px solid var(--rule); padding-top:1rem; }
  .stat + .stat { border-left:0; padding-left:0; border-top:1px solid rgba(185,188,178,.5); }
}
"""

FILTER_JS = """// Client-side filter over the record table, on pages that have one.
(function () {
  var q = document.getElementById('q');
  var out = document.getElementById('count');
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#rows tr'));
  function apply() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var hit = !term || row.dataset.search.indexOf(term) !== -1;
      row.hidden = !hit;
      if (hit) shown++;
    });
    out.textContent = term ? shown + ' of ' + rows.length + ' shown' : '';
  }
  q.addEventListener('input', apply);
  apply();
})();
"""

COLS = [
    "dateFiled",
    "defendant",
    "plaintiff",
    "caseName",
    "court",
    "court_citation_string",
    "court_id",
    "docketNumber",
    "suitNature",
    "cause",
    "docket_id",
    "docket_absolute_url",
]


def write_data_files(rows: list[dict]) -> None:
    with open(os.path.join(SITE, "cases.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(SITE, "cases.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "source": "CourtListener RECAP, https://www.courtlistener.com/api/rest/v4/",
                "licence": "CC0 1.0",
                "coverage_note": (
                    "Free PACER metadata carries no nature-of-suit code until a "
                    "docket is purchased into RECAP, so this record is a lower "
                    "bound on federal ADA Title III filings, not a census."
                ),
                "generated": dt.datetime.now(dt.timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "count": len(rows),
                "cases": [{k: r.get(k) for k in COLS} for r in rows],
            },
            fh,
            ensure_ascii=False,
            indent=1,
        )


def write_feed(rows: list[dict]) -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for r in rows[:50]:
        title = f"{r.get('caseName') or 'Filing'} ({court_of(r)})"
        desc = (
            f"Filed {longdate(r.get('dateFiled') or '')} in {r.get('court') or '—'}. "
            f"Docket {r.get('docketNumber') or '—'}. "
            f"Nature of suit: {r.get('suitNature') or '—'}."
        )
        items.append(f"""
    <item>
      <title>{html.escape(title)}</title>
      <link>{html.escape(CL + (r.get("docket_absolute_url") or ""))}</link>
      <guid isPermaLink="false">courtlistener-docket-{r.get("docket_id")}</guid>
      <description>{html.escape(desc)}</description>
    </item>""")
    with open(os.path.join(SITE, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>ADA Title III filings</title>
    <link>{html.escape(BASE_URL or CL)}</link>
    <description>New federal Americans with Disabilities Act Title III lawsuits, updated daily from CourtListener.</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>{"".join(items)}
  </channel>
</rss>
""")


def write_sitemap(paths: list[str]) -> None:
    today = dt.date.today().isoformat()
    if BASE_URL:
        urls = "".join(
            f"\n  <url><loc>{html.escape(BASE_URL + '/' + p)}</loc>"
            f"<lastmod>{today}</lastmod></url>"
            for p in paths
        )
        with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as fh:
            fh.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"{urls}\n</urlset>\n"
            )
    robots = "User-agent: *\nAllow: /\n"
    if BASE_URL:
        robots += f"Sitemap: {BASE_URL}/sitemap.xml\n"
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(robots)


# ------------------------------------------------------------------ main ----


def main() -> int:
    if not os.path.isdir(DATA_DIR) or not any(
        n.endswith(".ndjson") for n in os.listdir(DATA_DIR)
    ):
        print(f"no data in {DATA_DIR}; run scripts/fetch.py first", file=sys.stderr)
        return 1

    os.makedirs(os.path.join(SITE, "court"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "month"), exist_ok=True)
    rows = load()

    with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8") as fh:
        fh.write(STYLE)
    with open(os.path.join(SITE, "filter.js"), "w", encoding="utf-8") as fh:
        fh.write(FILTER_JS)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_page(rows))
    paths = ["index.html", "pulse.html"]

    by_court: dict[str, list[dict]] = {}
    for r in rows:
        by_court.setdefault(r.get("court_id") or "unknown", []).append(r)
    for cid, batch in by_court.items():
        # A court with a handful of filings has nothing to say on its own page,
        # and a thin page in the sitemap is worse than no page.
        if len(batch) < 5:
            continue
        with open(
            os.path.join(SITE, "court", f"{cid}.html"), "w", encoding="utf-8"
        ) as fh:
            fh.write(court_page(cid, batch))
        paths.append(f"court/{cid}.html")

    by_month: dict[str, list[dict]] = {}
    for r in rows:
        ym = (r.get("dateFiled") or "")[:7]
        if len(ym) == 7:
            by_month.setdefault(ym, []).append(r)
    order = sorted(by_month)
    for ym in order:
        with open(
            os.path.join(SITE, "month", f"{ym}.html"), "w", encoding="utf-8"
        ) as fh:
            fh.write(month_page(ym, by_month[ym], order))
        paths.append(f"month/{ym}.html")

    # The project's own scoreboard, published on the same terms as the filings.
    # Written last so the corpus figures it reports are this build's, not the
    # previous one's — pulse.py runs before the build and cannot know them, and
    # a page that disagrees with its own table teaches readers to distrust both.
    readings = load_pulse()
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    for reading in readings:
        if reading.get("date") == today:
            reading["cases"], reading["pages"] = len(rows), len(paths)
    with open(os.path.join(SITE, "pulse.html"), "w", encoding="utf-8") as fh:
        fh.write(pulse_page(rows, readings))
    if readings:
        with open(os.path.join(SITE, "pulse.ndjson"), "w", encoding="utf-8") as fh:
            for reading in readings:
                fh.write(json.dumps(reading, ensure_ascii=False, sort_keys=True) + "\n")

    write_data_files(rows)
    write_feed(rows)
    write_sitemap(paths)
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    print(
        f"built {len(paths)} pages from {len(rows)} filings "
        f"({len(by_court)} courts, {len(by_month)} months)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
