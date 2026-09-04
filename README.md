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

### What it does not cover

State-court actions, demand letters that never become suits, and anything a
clerk coded differently are invisible here. Most access disputes end in a
letter, so read the count as a floor. A caption names parties, not websites, and
does not say what the claim was about.

## Layout

```
scripts/fetch.py   pulls new filings, writes data/YYYY-MM.ndjson
scripts/build.py   renders site/ — index.html, cases.csv, cases.json, feed.xml
data/              the record, one file per filing month
.github/workflows/daily.yml   runs both, commits data, publishes the site
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
