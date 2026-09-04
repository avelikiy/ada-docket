#!/bin/bash
# The whole daily loop, runnable unattended: fetch new filings, record the
# measurable signals, rebuild the site, publish it, commit the data.
#
# This exists because GitHub Actions is unavailable on this account. The failure
# is account-wide and not ours to fix: a job is rejected in about three seconds
# having run zero steps and written no log, and the same thing happens on six
# unrelated repositories belonging to the same owner, the last success being in
# May. The repository is public with Actions enabled, so it is not a repository
# setting. GitHub's own pages-build-deployment still succeeds, which is why
# branch-based publishing keeps working while our workflow does not.
#
# So the schedule moved off GitHub and onto whatever machine runs this script.
# That is a downgrade and worth naming: a laptop asleep at the scheduled minute
# simply misses the day. It is still strictly better than a site that promises a
# daily record and silently stops updating, and `make schedule` makes the
# arrangement explicit and reversible instead of depending on somebody
# remembering to run a command.
#
# Safe to run more than once a day: the fetch is keyed on docket id and the
# pulse is keyed on date, so a second run corrects rather than duplicates.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1

# launchd hands a job a near-empty PATH — without this, git, gh and a modern
# python3 are all missing and every run fails identically at the first command.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily-$(date -u +%Y-%m).log"

say() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG"; }

say "=== run start ==="

status=0

# Each stage reports its own outcome and the run continues. A CourtListener
# hiccup should not cost us the rebuild of pages we already have data for, and
# a publish failure should not hide the fact that the fetch worked.
if python3 scripts/fetch.py --days 10 >>"$LOG" 2>&1; then
  say "fetch     ok"
else
  say "fetch     FAILED"; status=1
fi

# Measure how much of each month we hold, then spend what is left of the day's
# request allowance closing the largest hole. Both are resumable and both stop
# on their own at the budget, so this stage takes what time it takes and never
# starves tomorrow's fetch — the reserve is held back inside backfill.py.
#
# This is what makes the twelve-month gap close without anybody driving it. A
# backfill run by hand is what left April 2025 one day long, because a person
# ran it, hit the ceiling, and never came back to finish.
if python3 scripts/backfill.py >>"$LOG" 2>&1; then
  say "backfill  ok"
else
  # Exit 2 is the documented rate-limit stop, which is an ordinary outcome
  # here, not a failure: the run simply resumes tomorrow.
  rc=$?
  if [ "$rc" = "2" ]; then
    say "backfill  rate limit — resumes tomorrow"
  else
    say "backfill  FAILED"; status=1
  fi
fi

if python3 scripts/pulse.py >>"$LOG" 2>&1; then
  say "pulse     ok"
else
  say "pulse     FAILED"; status=1
fi

if python3 scripts/build.py >>"$LOG" 2>&1; then
  say "build     ok"
else
  say "build     FAILED"; status=1
  say "=== run end (status $status) ==="
  exit $status          # never publish a site we could not build
fi

if git diff --quiet -- data/ && git diff --cached --quiet -- data/; then
  say "commit    nothing new"
else
  git add data/ >>"$LOG" 2>&1
  if git commit -q -m "data: filings through $(date -u +%Y-%m-%d)" >>"$LOG" 2>&1 \
     && git push -q >>"$LOG" 2>&1; then
    say "commit    pushed"
  else
    say "commit    FAILED"; status=1
  fi
fi

if make publish >>"$LOG" 2>&1; then
  say "publish   ok"
else
  say "publish   FAILED"; status=1
fi

say "=== run end (status $status) ==="
exit $status
