# Market Re-check: ada-docket

**Author:** research-thompson · **Date:** 2026-09-04 · **Method:** live web search + direct fetch of competitor pages and the live ada-docket site. All claims below carry a URL. Confidence is marked `[confirmed]` / `[likely]` / `[speculative]`.

**Verdict up front: THESIS DEAD.** Not "the market rejected us" — the market never saw us. The long-tail-SEO thesis was structurally unwinnable before the first cycle, for reasons that a 20-minute search would have surfaced. Details below; the single residual wedge (which is *not* SEO) is in §5.

---

## 1. Competitive reality: who owns this search space

The strategy docs treat this as an empty field. It is not. One afternoon of searching surfaced **15 distinct properties** publishing ADA Title III filing data, in four structurally different layers.

### Layer 1 — Primary docket layer (upstream of everyone, including us)

| Property | What it is | Why it matters to us |
|---|---|---|
| [CourtListener / RECAP](https://www.courtlistener.com/) | Our own data source. Free API, free public docket pages, huge domain authority. | **We republish our supplier's public pages.** Google already indexes the canonical version of every case we list. We link *to* them from every row. |
| [Justia Dockets](https://dockets.justia.com/browse/state-florida/court-flmdce/noscat-5) | Free browse-by-court, browse-by-nature-of-suit, per-case pages, per-state indexes. Surfaced in search for court-level Florida ADA queries. `[confirmed]` | This is *literally the page structure ada-docket built*, shipped years ago on a DA-80+ domain. |
| UniCourt, PacerMonitor, Docket Alarm | Commercial docket aggregators with free-tier indexed pages. | Own defendant-name and case-name queries. |

### Layer 2 — Editorial authority layer (the citation source)

| Property | Cadence | Granularity |
|---|---|---|
| [Seyfarth Shaw / adatitleiii.com](https://www.adatitleiii.com/) | Annual + mid-year, since 2013 | Hand-coded from PACER with a stable taxonomy. 8,667 federal Title III suits in 2025, −2% YoY; CA 3,252 / FL 1,823 / NY 1,471. `[confirmed]` |
| [UsableNet](https://info.usablenet.com/ada-website-compliance-lawsuit-tracker) | **Monthly, free** | Federal **plus NY and CA state courts**; industry, company size, widget vendor, plaintiff firms. `[confirmed]` |
| [EcomBack](https://www.ecomback.com/annual-2024-ada-website-accessibility-lawsuit-report) | **Monthly + annual, free** | **Per-court, per-firm, per-state, per-month, per-industry.** SDNY 1,090 cases = 68.13% of NY. Stein Saks 428 filings = 13.43% of all cases. 23 industry categories. `[confirmed]` |

### Layer 3 — Derivative / vendor-funded SEO layer (our actual competitive set)

[accessibility.build](https://accessibility.build/research/accessibility-lawsuits) · [WCAGsafe](https://wcagsafe.com/blog/ada-lawsuit-statistics) · [Abledly](https://abledly.com/ada-lawsuit-statistics) · [beaccessible](https://beaccessible.com/post/americans-with-disabilities-act-statistics/) · [disabilityworld](https://www.disabilityworld.org/articles/serial-plaintiffs-versus-individuals/) · [accessibilitychecker.org](https://www.accessibilitychecker.org/blog/ada-title-iii/) · [Accessibility.Works](https://www.accessibility.works/blog/new-york-federal-state-ada-website-compliance/) · [Level Access](https://www.levelaccess.com/blog/title-iii-lawsuits-10-big-companies-sued-over-website-accessibility/) · [adaquickscan](https://adaquickscan.com/blog/florida-ada-website-lawsuits-1627-cases-serial-plaintiff) · [RatedWithAI](https://ratedwithai.com/blog/gainesville-ada-lawsuits-small-business-lessons-2026) · [Kha Creation](https://khacreationusa.com/ada-title-iii-website-lawsuits/) · [accessible.org](https://accessible.org/ada-website-plaintiffs-law-firms/) (40-firm directory) · [adabook.com](https://adabook.com/plaintiffs-law-firms-stein-saks-mark-rozenberg/) (per-firm pages) · [krisrivenburgh.com](https://krisrivenburgh.com/stein-saks-pllc-mark-rozenberg-ada-website-lawsuits/) (per-firm **and per-plaintiff** pages) · [karlinlaw.com](https://www.karlinlaw.com/stein-saks-llp-mark-rozenberg-example-lawsuit2/)

### Layer 4 — Paid analytics (where the people with budget actually are)

Lex Machina (LexisNexis, [no public pricing, demo-gated](https://www.lexisnexis.com/en-us/products/lex-machina.page)), Bloomberg Law, Docket Alarm, Trellis. `[confirmed]`

### Does the long tail hold?

I tested the exact query shapes ada-docket bets on:

| Query tested | Who ranks | Is ada-docket there? |
|---|---|---|
| `"ADA lawsuits filed in" Middle District of Florida 2026` | natlawreview, **Justia Dockets (court-level browse)**, adaquickscan, RatedWithAI, local news | No |
| `Stein Saks PLLC ADA lawsuits filed list` | accessible.org, **EcomBack monthly reports**, **adabook per-firm page**, **krisrivenburgh per-firm page**, karlinlaw | No |
| `"ADA lawsuits filed" SDNY statistics` | EcomBack, adatitleiii.com, uscourts.gov, Accessibility.Works | No |
| `"ADA Title III" filings "Eastern District of New York" monthly count` | adatitleiii.com, disabilityworld, beaccessible | No |
| `ada-docket avelikiy.github.io ADA Title III filings` (brand+site) | adatitleiii.com, ABA, disabilityworld | **No — not even for its own name** |

**Finding `[confirmed]`:** the long tail is **not** open. Firm-level is occupied by four dedicated properties. Court-level is occupied by Justia's docket browse *and* by EcomBack's per-court monthly numbers. State-level is occupied by everybody, including Seyfarth's own state table.

**The one genuine hole:** no Layer-2/3 property publishes a *per-district monthly time series*. When I pushed on the EDNY monthly query, the best answer available was "you may need to access PACER directly." That is a real content gap. It is a gap because nobody wants it — see §3.

**And the brand-query result is the whole story.** After 7 cycles the site does not surface for its own name. It is not a ranking problem; it is a not-in-the-index problem.

---

## 2. Differentiation: is there anything the incumbents structurally cannot do?

I checked each claimed differentiator against what competitors actually ship today.

| Claimed edge | Reality | Verdict |
|---|---|---|
| **Machine-readable CSV/JSON** | accessibility.build ships **CSV downloads per dimension, JSON endpoints, and a whole-dataset JSON download**. `[confirmed]` | **Gone.** Shipped by a competitor launched in 2026. |
| **Permissive licence** | accessibility.build is **CC BY 4.0**. ada-docket is CC0. CC0 is marginally freer. `[confirmed]` | **Rounding error.** Nobody chooses a dataset on CC0-vs-CC-BY. |
| **Per-court granularity** | EcomBack publishes per-court counts monthly; Justia publishes per-court case browse. `[confirmed]` | **Gone.** |
| **Per-firm pages** | EcomBack (with counts + %), accessible.org (40-firm directory), adabook, krisrivenburgh (firm *and* plaintiff pages). `[confirmed]` | **Gone**, though our version is deeper on counts than accessible.org's and deeper on case lists than adabook's (which turned out to be a single-complaint video writeup, not a case index). `[confirmed]` |
| **Daily freshness vs annual reports** | True — UsableNet is monthly, Seyfarth is semi-annual, EcomBack is monthly. ada-docket rebuilds daily. | **Real but worthless.** Nobody has a decision that changes on a one-day-old ADA filing count. Freshness only pays where it changes an action (an alert on *your* name — see §5). A daily-refreshed aggregate is a vanity metric. |
| **Per-case, defendant-named index** | EcomBack explicitly "does not provide comprehensive defendant listings." `[confirmed]` Neither does Seyfarth, UsableNet, or accessibility.build. | **The only surviving differentiator vs Layers 2–3 — but it is Justia/UniCourt/CourtListener's home turf, and we link to CourtListener as the canonical source on every row.** |
| **Structural coverage** | ada-docket is **federal-only**. UsableNet already covers **NY and CA state courts**; SDNY's Chief Judge has been pushing web-only ADA cases out of federal court, moving volume to state court. `[confirmed]` | **Negative differentiation.** We are federal-only in a market where the growth is state-court. |

### The disqualifying structural facts

Two things are worse than "no differentiation," and neither appears in the strategy docs:

1. **`github.io` is a public suffix.** A `*.github.io` subdomain accrues no domain authority from github.io and is treated as an independent, zero-trust host. We are competing for commercial-intent queries against DA-80+ properties from a permanent DA-0 position, with no custom domain. `[confirmed — this is how the public suffix list works]`

2. **The artifact advertises its own incompleteness.** The live homepage currently reads: *"2,705 filings tracked across 68 district courts,"* Jan 2025–Sep 2026, and — in its own words — **"12 months have not been collected at all (May 2025 to April 2026)."** `[confirmed — fetched 2026-09-04]` Half the window is empty and the page says so. Against Seyfarth's 13-year hand-coded series, this is not a data product; it is a partial mirror of a free API, and it is honest enough to admit it. (Note: this contradicts the "2,638 filings / 21 months / 30.7%" figure in the brief — the live site says 2,705 and a 12-month hole.)

**Ben Thompson framing:** Seyfarth's moat is not the data — the data is public. The moat is **13 years of manual coding under a stable taxonomy**, which is what makes the number *citable*. Everyone downstream, including the 2026-launched accessibility.build, builds on Seyfarth's series *rather than on raw court data* — even though raw court data is free to everyone. That is the market telling you, unambiguously, that **the scarce good is trusted classification, not machine access to filings.** ada-docket automated the abundant half and skipped the scarce half.

---

## 3. Demand: does anyone search these queries?

**Direct evidence I could not obtain `[gap]`:** no keyword-volume tool was available, so I have no numeric MSV. What I have is behavioural inference, which is weaker but pointed in one direction only.

**Inference `[likely]`:** court-level, firm-level and month-level ADA filing queries have near-zero commercial volume.
- If they had volume, EcomBack — which *already computes* per-court and per-firm numbers monthly — would have built landing pages per court and per firm. It publishes them buried inside monthly report posts instead. A specialist with the data and the SEO incentive declined to build the page structure ada-docket built 114 of. That is a revealed-preference signal against the query class.
- Google's own synthesis for the EDNY monthly query concluded "you may need to access PACER directly" — i.e. no page in the index targets it, after years of a highly SEO-motivated vendor field. Unoccupied ground in a contested field is unoccupied for a reason.

**Who the actual audiences are, and what they already use:**

| Audience | What they actually need | Already served by | Would ada-docket displace it? |
|---|---|---|---|
| **Defense counsel** (Seyfarth, Jackson Lewis, Fox Rothschild, Morgan Lewis, Kaufman Dolowich — all with standing Title III practices `[confirmed]`) | Complaint PDFs, party litigation history, judge analytics, docket alerts, standing-argument precedent | Lex Machina / Bloomberg Law / Docket Alarm, firm-billable | **No.** They need the document and the alert; we give a count and a link back to CourtListener. |
| **Plaintiff firms** | Their own filings; target lists | PACER; internal | No. |
| **Retail / corporate compliance** | "Am I at risk? What does it cost?" | Layer-3 vendor content (avg settlement ~$30k, 94.8% of sites fail WCAG `[confirmed]`) | No — they search head terms, which are saturated. |
| **Journalists** | A quotable annual number with a credible name on it | Seyfarth | **No — and this is the killer.** Citability *is* the product, and it is exactly what an anonymous github.io mirror cannot supply. |
| **Accessibility vendors** | Lead-gen content + a defensible statistic | They publish their own | Possibly as a *supplier* — see §5. |

**The economics nobody modelled `[confirmed by structure]`:** every Layer-3 site is loss-leading content funded by a back end — WCAG remediation retainers, overlay subscriptions, audits, demand-letter response. A ~$30k average settlement makes a $5–15k remediation contract easy to sell, which is what pays for the content. **ada-docket is competing on their content axis with none of their economics.** Zero revenue is not a stage; it is the whole plan. Even total SEO victory produces $0.

---

## 4. Why 7 cycles produced nothing — the honest read

It is tempting to say "SEO takes 6–12 months, be patient." That is not what happened here. Five independent failures, any one of which is sufficient:

1. **No indexable presence.** The site doesn't rank for its own name; the homepage has no XML sitemap `[confirmed — fetched]`. Nothing has entered the funnel to be patient about.
2. **Permanent DA-0 host.** `github.io` cannot accumulate authority. Competing for commercial queries from there is not slow; it is closed.
3. **Both differentiators already shipped by rivals** (CSV/JSON + permissive licence → accessibility.build; four-way granularity → EcomBack).
4. **No demand at the chosen granularity**, evidenced by a motivated competitor declining to build those pages.
5. **No monetization path even on success.**

And one more: cycles 1–7 were spent on **backfill completeness** — a supply-side problem, at ~105 requests/day, against a source that is free and public. Under Aggregation Theory the supply side of this market is not scarce; it is free. Effort went into the abundant input while the scarce input (trust, distribution, a domain, a name) got zero cycles. Seven cycles of supply-side work in a market whose only scarcity is demand-side.

---

## 5. The one wedge, and it is not SEO

If anything survives, it is not the destination site. Three candidates, ranked by evidence:

**(a) Be the structured-data supplier to Layer 3. `[likely]` — the strongest signal I found.**
accessibility.build launched in 2026 and built on *Seyfarth's manually-reviewed series* rather than on raw court data — despite raw court data being free. `[confirmed]` That is a demonstrated, dated instance of someone wanting clean structured ADA filing data and choosing a hand-curated PDF series over the API. EcomBack, WCAGsafe, Abledly, beaccessible and a dozen vendor blogs re-derive the same numbers by hand every month. ada-docket already has the pipeline that would serve them. **But be honest about the size: this is a 5–15 customer market at maybe $50–200/mo, and it requires the one thing we don't have — a credible classification methodology, i.e. exactly Seyfarth's moat.** It is also a sales motion, not an SEO motion, and this company has never run one.

**(b) Named-entity pages with alerts — defendant names and serial-plaintiff names. `[speculative]`**
The only query class here with urgent, monetizable intent: "was *my company* named," "who is *this plaintiff* suing." No Layer-2/3 property publishes defendant listings `[confirmed]`. krisrivenburgh has some plaintiff pages `[confirmed]`. **Skeptical read: Justia, UniCourt and CourtListener already own name queries with 80x our authority, and we link to CourtListener as canonical on every row.** Freshness finally means something here (an alert on your name is a decision), but it needs a real domain, email capture, and a paid tier — a different product with a different cost structure, not a next cycle of this one.

**(c) Federal-only is a dead frame.** Whatever gets built, UsableNet already covers NY and CA state courts and SDNY is pushing web-only cases out of federal court. `[confirmed]` A federal-only dataset is measuring a shrinking share of the phenomenon.

### What I don't know `[gaps]`
- **No keyword volume numbers.** Everything in §3 is behavioural inference. Cheapest fix: one month of Google Search Console on a real domain — that answers "is there any demand" with data instead of argument, and costs ~$12 for a domain.
- **Whether Layer-3 sites would actually pay for data.** Unresolvable by search. Ten cold emails to accessibility.build, WCAGsafe, Abledly, beaccessible and adaquickscan settles it in a week — and is the only cheap experiment on this page.
- **Whether Seyfarth/UsableNet would license or partner** rather than compete. Not investigated.

---

## Recommendation (separated from the facts above)

Stop backfilling. Completing a 30%-covered mirror of a free public API buys nothing that any competitor lacks. If the team wants one more swing, spend it on **(a)** — ten cold emails, one week, zero code — because it is the only hypothesis on this page supported by a dated, observed fact rather than by inference. If those emails go unanswered, the honest move is to keep the CC0 dataset published as a public good and reallocate every remaining cycle.

---

**THESIS DEAD** — the long-tail-SEO distribution bet is structurally closed (DA-0 host, both differentiators already shipped by rivals, no demand at the chosen granularity, no monetization on success); the only residual wedge is B2B structured-data supply to the vendor content layer, which is a sales motion, not an SEO one.
