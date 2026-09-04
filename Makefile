SITE_URL ?= https://avelikiy.github.io/ada-docket
REPO     ?= https://github.com/avelikiy/ada-docket.git
export SITE_URL

# Everything below runs on a stock Python 3.9+ with no dependencies.

.PHONY: update pulse build serve publish daily backfill status coverage plan test schedule unschedule schedule-status

REPO_DIR := $(shell pwd)
PLIST    := $(HOME)/Library/LaunchAgents/com.ada-docket.daily.plist
LABEL    := com.ada-docket.daily

update:            ## pull the last ten days of filings into data/
	python3 scripts/fetch.py --days 10

pulse:             ## record today's measurable signals into metrics/pulse.ndjson
	python3 scripts/pulse.py

build:             ## render site/ from data/
	python3 scripts/build.py

serve: build       ## read it locally
	python3 -m http.server 8000 --directory site

# Publishes the built site to the gh-pages branch, which GitHub Pages serves.
# This is the same thing the daily workflow does, runnable by hand — the site
# keeps updating even when Actions is unavailable on the account.
publish: build
	@rm -rf .publish && cp -R site .publish
	@cd .publish && git init -q -b gh-pages && git add -A \
	  && git commit -q -m "site: build $$(date -u +%Y-%m-%d)" \
	  && git push -q -f $(REPO) gh-pages
	@rm -rf .publish
	@echo "published to $(SITE_URL)"

daily:             ## the whole loop: fetch, measure, render, commit, publish
	@bash scripts/daily.sh

# The daily loop has to live somewhere. GitHub Actions is unavailable on this
# account — jobs are rejected in three seconds with no log, on six unrelated
# repositories, since May — so the schedule runs locally instead. This installs
# exactly one file and `unschedule` deletes it; nothing else on the machine is
# touched. A laptop asleep at the scheduled minute misses that day, which is the
# honest cost of not having a server.
schedule:          ## install the local daily schedule (one file, reversible)
	@mkdir -p "$(HOME)/Library/LaunchAgents" logs
	@sed 's|__REPO__|$(REPO_DIR)|g' scripts/launchd.plist.in > "$(PLIST)"
	@launchctl bootout "gui/$$(id -u)/$(LABEL)" 2>/dev/null || true
	@launchctl bootstrap "gui/$$(id -u)" "$(PLIST)"
	@echo "scheduled daily at 07:20 local — $(PLIST)"
	@echo "remove it with: make unschedule"

unschedule:        ## remove the local daily schedule
	@launchctl bootout "gui/$$(id -u)/$(LABEL)" 2>/dev/null || true
	@rm -f "$(PLIST)"
	@echo "unscheduled; $(PLIST) removed"

schedule-status:   ## is the local schedule installed and loaded?
	@test -f "$(PLIST)" && echo "plist   present" || echo "plist   absent"
	@launchctl print "gui/$$(id -u)/$(LABEL)" 2>/dev/null \
	  | awk '/state = |last exit code|run count/ {gsub(/^ +/,""); print "agent   " $$0}' \
	  || echo "agent   not loaded"

# Close the holes in the record. Resumable and budget-aware: it measures each
# month against the court index, then spends what is left of the day's request
# allowance on the emptiest month and stops. Running it again tomorrow continues
# from data/coverage.json. The daily job already does this, so run it by hand
# only to hurry things along.
backfill:
	python3 scripts/backfill.py

status:            ## what we hold per month, read from the last measurement; spends nothing
	python3 scripts/status.py

coverage:          ## re-measure every month against the court index (SPENDS ~1 request a month)
	python3 scripts/backfill.py --audit-only

plan:              ## what the backfill would do next, spending nothing
	python3 scripts/backfill.py --plan

test:              ## the whole suite; standard library, nothing to install
	python3 -m unittest discover -s tests -v
