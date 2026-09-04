# ADA Title III filings

A daily record of federal Americans with Disabilities Act Title III lawsuits,
built from the public court docket. Defendants, plaintiffs, courts, docket
numbers, and counsel of record — free, no account, CSV and JSON and RSS.

**Site:** published by GitHub Pages from `site/` on every run.

## Why this exists

ADA Title III filings run past 3,000 a year in federal court and the count keeps
climbing, but there is no free, current, machine-readable list of who is being
sued. Annual PDF reports from consultancies arrive months late; the docket
services that are current cost thousands a year. The record itself is public.
This publishes it, every day, in the shape a person or a script can actually use.

## What is in the record

A filing enters when its docket carries nature of suit **446** (Americans with
Disabilities — Other) or **443** (Accommodations). That is where the Title III
bar files, web-accessibility cases included.

| Field | Meaning |
|---|---|
| `dateFiled` | Filing date as the court recorded it |
| `defendant`, `plaintiff` | Read from the case caption |
| `caseName` | The caption verbatim |
| `court`, `court_id`, `court_citation_string` | Deciding district |
| `docketNumber` | The court's own number |
| `suitNature`, `cause` | Clerk's coding |
| `docket_absolute_url` | Path to the docket on CourtListener |

### How complete each month is

A month page states what it holds and, when that is short of what the court
index reports, says so and shows the shortfall. This is measured rather than
assumed: the search endpoint reports a `count` for any window regardless of how
many pages a crawl walked, so one request a month settles it, and the result is
kept in `data/coverage.json`.

The distinction matters because it was got wrong. A backfill that stops at the
rate ceiling leaves a month that looks, to everything downstream, exactly like a
quiet month — the stored rows record what came back, never what was asked for.
April 2025 was published as "25 filings, 0.8 a day" on that basis; the index
reports about 409. Weeks we have not collected now draw as ruled columns rather
than as noughts, for the same reason.

`make status` prints what we hold and spends nothing, `make coverage`
re-measures it against the court index at about one request a month, `make
plan` says what the backfill would do next, and the daily run does the
measuring and the repairing without being asked.

Reach for `make status` first. Re-measuring costs twenty-one of the day's
hundred and twenty-five requests, and a check that expensive is a check that
gets skipped — which is how a truncated April got published as a whole month
in the first place.

### What it does not cover

State-court actions, demand letters that never become suits, and anything a
clerk coded differently are invisible here. Most access disputes end in a
letter, so read the count as a floor. A caption names parties, not websites, and
does not say what the claim was about.

## Layout

```
scripts/fetch.py     pulls new filings, writes data/YYYY-MM.ndjson
scripts/coverage.py  how much of each month we hold, measured not assumed
scripts/backfill.py  audits coverage and closes the holes, a day's budget at a time
scripts/build.py     renders site/ — index.html, cases.csv, cases.json, feed.xml
scripts/daily.sh     the whole loop, run unattended by launchd
data/                the record, one file per filing month
data/coverage.json   what the court index reports per month, against what we hold
tests/               standard library unittest; `make test`
```

The record is partitioned by month on purpose. One combined file would be
rewritten in full every day, and years of daily rewrites of a multi-megabyte
blob turn the git history into tens of gigabytes. Partitioned, only the current
month moves.

## Running it

Python 3.9+, no dependencies — standard library only, so the daily job needs no
install step.

```sh
python3 scripts/fetch.py --days 10          # recent filings
python3 scripts/fetch.py --since 2025-01-01 --until 2025-02-01   # backfill a month
python3 scripts/build.py                    # render site/
python3 -m http.server 8000 --directory site
```

`fetch.py` is idempotent: filings are keyed on CourtListener's docket id, so
re-running a window never duplicates a case. The daily job overlaps ten days
because dockets sometimes reach RECAP late.

## Source and licence

Dockets come from [CourtListener](https://www.courtlistener.com), a service of
the Free Law Project, through its public REST API. Federal court records are not
subject to copyright; this compilation is released under CC0. Please credit the
Free Law Project — the data exists because they maintain it.

## Not a screening product

This is a mirror of the public docket, published for research. It is not legal
advice and it is not a consumer report: it must not be used to make decisions
about any individual's credit, employment, housing, or insurance. Court records
contain errors. Verify against the docket before relying on anything here.

## Publishing

The site is served from the `gh-pages` branch. `make publish` renders `site/` and
force-pushes it there; `make daily` runs the whole loop — fetch, measure, render,
commit the record, publish. Branch-based Pages was chosen over an Actions
artifact deliberately, and that decision turned out to carry the project.

### Where the schedule runs, and why it is not GitHub

`.github/workflows/daily.yml` still describes the job, but it does not run.
Actions is unavailable on this account: a job is rejected in about three seconds
having executed zero steps and written no log, and the same thing happens on six
unrelated repositories under the same owner, the last success being in May. The
repository is public with Actions enabled and `allowed_actions: all`, so it is
not a repository setting. GitHub's own `pages-build-deployment` still succeeds,
which is why publishing from a branch keeps working while our workflow does not.
Unblocking it needs a person in the account's billing settings; nothing in this
repository can fix it.

So the schedule runs locally instead:

```sh
make schedule          # install one launchd agent, daily at 07:20 local
make schedule-status   # is it installed and loaded?
make unschedule        # remove it — this is the entire uninstall
```

`make schedule` writes exactly one file,
`~/Library/LaunchAgents/com.ada-docket.daily.plist`, and touches nothing else.
It runs as a user agent rather than a daemon so the job can reach the keychain
holding the git credentials.

**The weak point, stated plainly:** a laptop asleep at 07:20 misses that day
outright. This is worse than a hosted scheduler and better than a site that
promises a daily record and quietly stops. Runs append to `logs/daily-YYYY-MM.log`;
each stage reports its own outcome, and a build failure stops the run before it
can publish a broken site.

## Measuring it

`make pulse` records, once a day, the signals that are free to read without an
account: Feedly's public subscriber count for the feed, repository stars and
watchers, GitHub's fourteen-day repository traffic, and the size of the corpus.
Readings accumulate in `metrics/pulse.ndjson` and are published at
[`/pulse.html`](https://avelikiy.github.io/ada-docket/pulse.html). They live
outside `data/` on purpose: everything in `data/` is read as filings, and a
readings file sitting there once killed the daily fetch outright while the
site went on publishing as though nothing had happened.

The page exists to publish a gap rather than hide it. This project set itself a
closing condition before launch — fewer than fifty subscribers or fewer than a
hundred and twenty unique readers at ninety days and it shuts down — and only
afterwards established that unique readers are not observable at all from a
static site on github.io. GitHub reports no traffic for Pages, and the
alternatives each need a server, a paid account, or a Search Console sign-in.
That half of the condition is therefore published as blank ruled lines. A proxy
in that column is how a closing condition quietly stops meaning anything.

### The one step that needs a person

Whether any of these 134 pages has ever appeared in a search result is not a
hard question here — it is an unanswerable one from the inside. Static Pages
writes no logs we can read, and GitHub's traffic API counts the repository
rather than the site. Long-tail search is the whole distribution plan, and its
first step has never been measured.

Search Console answers it, and nothing else free does. The build side is
already wired, so what remains is:

```
1. search.google.com/search-console → Add property → URL prefix
   (not "Domain" — that needs a DNS record, and github.io takes none)
   https://avelikiy.github.io/ada-docket/
2. Choose "HTML tag", paste the line it shows into verification.txt
3. make publish
4. Press Verify
```

`verification.txt` carries the same walkthrough in its comments and does
nothing until a token is added. Indexing data is not retroactive: it starts
from the day this is done, which is the argument against waiting for a tidier
moment.

### Known gap

Requests run unauthenticated against CourtListener's public API. That is inside
the documented limits for the daily job — about four requests against a ceiling
of 125 a day — but a backfill is throttled hard, and Free Law Project asks
anyone building a product on the API to arrange a commercial agreement first.
Registering an API token, and opening that conversation before any paid use, is
outstanding.
