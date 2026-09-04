SITE_URL ?= https://avelikiy.github.io/ada-docket
REPO     ?= https://github.com/avelikiy/ada-docket.git
export SITE_URL

# Everything below runs on a stock Python 3.9+ with no dependencies.

.PHONY: update build serve publish daily backfill

update:            ## pull the last ten days of filings into data/
	python3 scripts/fetch.py --days 10

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

daily: update publish  ## the whole loop: fetch, render, publish
	@git add data/ && git diff --cached --quiet \
	  || git commit -q -m "data: filings through $$(date -u +%Y-%m-%d)"

# Backfill one month at a time. CourtListener allows five requests a minute, so
# a month takes a few minutes; that is the polite pace, not a bug.
#   make backfill FROM=2025-05-01 TO=2025-06-01
backfill:
	python3 scripts/fetch.py --since $(FROM) --until $(TO) --max-pages 120
