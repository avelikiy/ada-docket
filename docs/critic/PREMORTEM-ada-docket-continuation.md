# PREMORTEM — ada-docket: continue or kill

**Reviewer:** critic-munger · **Date:** 2026-09-04 · **Question put to me:** continue or kill.

**Judgment, one line: VETO further engineering investment. Keep the asset running at zero
cost. But the case for killing that I was handed is half wrong, and the half that is wrong
is more dangerous to this company than ada-docket is.**

---

## 0. Before anything else: I checked the facts, and two of them are not what you think

I was told to be ruthless. Being ruthless starts with the brief I was handed, not with the
project. Two of the premises I was given are false, and I verified both myself.

### 0.1 The project is four hours old. Not ninety days. Four hours.

```
GitHub API:  createdAt 2026-09-04T06:13:35Z   pushedAt 2026-09-04T07:40:51Z
git log:     first commit 08:13:27 +0200   last commit 09:40:50 +0200   (17 commits)
```

Every one of the "~7 build cycles" fits inside **87 minutes of commit history**. The repo
did not exist before breakfast. And you are asking me whether to close it under a rule that
says "no audience connection by **day 90**."

Day 90 is in December. We are on hour four.

So let me dispose of the headline evidence immediately:

| "Fact" as presented | What it actually measures |
|---|---|
| 0 subscribers after 7 cycles | 0 subscribers after 87 minutes |
| 0 stars, 0 repo views | Nobody was told the repo exists. Nobody was going to guess. |
| 0 evidence a human visited | Correct, and it would be alarming in November and is meaningless today |

**A newborn has not failed to walk.** Presenting four hours of silence as a failed
distribution experiment is not rigour, it is theatre. If I approved a kill on that evidence
I would be ratifying a broken instrument, and the next project would be killed by the same
broken instrument for the same non-reason.

**The instrument is the finding.** This company measures time in *cycles* and then applies
rules written in *days*. Seven cycles took 87 minutes. Four "unclosed human gates" took
about forty minutes — during which the human was, one presumes, having coffee. The company
has invented a metabolic rate no calendar and no person can match, and is now filing
grievances against reality for not keeping up.

That error will outlive this project. Fix that or every future post-mortem is fiction.

### 0.2 "Whether any page is indexed is unknown and needs a human" — false. I answered it in ninety seconds, for nothing.

`verification.txt` states, in a comment block written with real conviction:

> "has Google indexed any of these 134 pages?" is not a hard question here — it is an
> unanswerable one, from the inside. […] Connecting Search Console is the only thing that
> changes that.

That is wrong, and it blocked four cycles. Search Console tells you *which queries brought
which impressions*. It is not the only way to learn *whether you are in the index at all*.
A `site:` query answers that, from outside, free, in seconds, with no human:

```
$ curl -s "https://www.bing.com/search?q=site%3Aavelikiy.github.io%2Fada-docket"
  → "There are no results"        (result block class b_no; zero <cite> hits)

WebSearch "site:avelikiy.github.io/ada-docket"
  → zero results from the domain

WebSearch "ada-docket federal ADA Title III lawsuit filings tracker"
  → 9 results. adatitleiii.com ×3, accessibility.build, beaccessible, wcagsafe,
    disabilityworld ×2. Ours: absent.
```

Site is live (`200`), `robots.txt` `200`, `sitemap.xml` `200`. **Zero pages indexed.**

That is the exact number Search Console would have shown, obtained without the human, and it
was available on cycle one. Four cycles were spent writing increasingly eloquent
documentation explaining why a question could not be answered — and the documentation was
better written than the question was hard.

**This is the lesson worth more than the project:** before you declare something blocked on
a human, spend ninety seconds asking whether you have merely failed to think of the second
route. "We cannot know" is the most expensive sentence in this repo. It was also false.

*(And note the asymmetry: zero pages indexed after four hours is not evidence of failure
either. Google does not crawl a link-less github.io subpath in an afternoon. The number is
uninformative today. What makes it informative is that we can now take it again tomorrow,
and next week, for free, forever — which is what a real gate looks like.)*

---

## 1. INVERSION — it is March 2027 and continuing was obviously wrong

Assume the failure. Here is the autopsy, written in advance. I am not listing risks; I am
telling you what the coroner will say.

### Cause of death #1 — It could never take money, and we knew that on day one

No KYC → no payment rail → structurally $0 revenue **at any traffic level**. Not "hard to
monetise." Not "monetisation deferred." *Impossible.* A ten-thousand-visitor month and a
zero-visitor month produce the identical bank balance.

The company's stated mission is four words: **make money legally.** We spent our build
capacity on the one asset in the portfolio that is mathematically incapable of satisfying it.

The coroner's line: *they optimised the conversion funnel of a machine with no coin slot.*

### Cause of death #2 — We shipped worse data, for free, into a market already served free

| Who | What they publish | Since | Price |
|---|---|---|---|
| Seyfarth Shaw (adatitleiii.com) | Annual + mid-year federal ADA Title III counts, by state, by category, lawyer-reviewed, with commentary | 2013 | Free |
| UsableNet | Monthly tracker | — | Free |
| accessibility.build | 2026 lawsuit tracker, built on Seyfarth's cleaned numbers | 2026 | Free |
| **ada-docket** | **30.7% of filings; 14 of 21 months incomplete; no review** | **today** | Free |

Seyfarth's own page in the live search results reports **8,667 filings for 2025**, broken
out by state, with website-accessibility share. We hold **2,638 of 8,582 (30.7%)** and are
grinding nights of anonymous API budget to catch up to a number a law firm has published
free every year since 2013 — and publishes *with a human checking it*, which we do not and
cannot.

We are not cheaper (both free). We are not better (30.7% vs complete). We are not faster in
any way a reader can perceive. **We picked a fight with an incumbent on their axis and
brought a third of the data.**

The coroner's line: *they entered a free market as the worse free option.*

### Cause of death #3 — The content has no shape that Google rewards

I checked the dataset itself rather than assuming. Across all 2,705 held rows:

```
distinct defendants:                    2,618
defendants appearing ≥5 times:              0
largest single defendant:                   4   (Sunshine Gasoline Distributors, Inc.)
```

**2,618 distinct defendants across 2,705 filings.** There is no repeat structure. No
"companies most sued" page, no entity that accumulates authority, no hub worth linking to.
Each row is a one-off. What we have is 134 thin pages of near-unique records with zero
inbound links, competing for queries owned since 2013 by a law firm with a national brand.

Long-tail SEO is a real strategy. It is a strategy for content that *aggregates* —
where the hundredth page makes the first page stronger. Ours does not aggregate. It piles.

The coroner's line: *they bet everything on a distribution channel their content was the
wrong shape for, and never checked the shape.*

### Cause of death #4 — "Free daily updates" was a promise resting on one laptop

`.github/workflows/daily.yml` exists and is well written. GitHub Actions is **billing-locked
account-wide** — every run dies in seconds. The real runner is `com.ada-docket.daily`, a
launchd job on the user's Mac, which as of the last check had **`runs = 0`**.

Every page on this site claims to be a daily record. The daily-ness depends on one personal
machine being awake at 07:20, forever, with nobody watching whether it was. On the first
morning it wasn't, we published a stale site that still called itself daily — and we know
that failure mode is live, because it already happened once today (fetch failed 06:30:50,
publish succeeded 06:30:56, six seconds apart, site shipped anyway).

The coroner's line: *the product's central claim had a single point of failure that was
someone's sleep schedule.*

### Now invert: what would have had to be true?

| Required for success | True today? |
|---|---|
| A way to collect money | **No.** KYC undone. Structural. |
| A dimension where we beat free incumbents | **No.** Worse data, same price, no review. |
| Content that aggregates into authority | **No.** 2,618 defendants / 2,705 rows. |
| A distribution channel we can influence at $0 | **No.** Zero backlinks, zero index presence, no promotion attempted. |
| An identified user with a named unmet need | **No.** No user was ever named. Not one. |
| Data completeness competitive with incumbents | **No.** 30.7%, and closing it needs a token nobody registered. |
| A reliable publish pipeline | **Partly.** Code is good; the runner is one sleeping laptop. |

**Seven conditions. Zero met. One partly.** That is not a project needing another cycle.
That is a project that never had a thesis — it had a data source and a team that enjoyed
building.

---

## 2. THE SUNK-COST TEST — separating "well-built" from "should exist"

Let me say the true thing first, because it costs me nothing and it is deserved: **this
codebase is good.** 59 tests. Real invariants — the partition-name check, the coverage
model that measures against the source instead of against itself, refusing to publish months
we only partly hold. Honest error handling that reports a spent rate limit as a sentence
instead of a traceback. A legal review that went and *queried the dataset* to prove the
plaintiff-page defect empirically instead of theorising about it. Rate limits set
deliberately conservative because hammering a nonprofit's free API is rude.

That is better engineering discipline than most funded startups have. It is also **entirely
beside the point**, and here is the tell: *every one of those virtues would be equally true
if the site published nothing at all.*

Now the arguments for continuing, and what each one actually is:

| Argument you will hear | What it really is |
|---|---|
| "We're at 30.7% — it'd be a shame to stop before the data is complete" | **Sunk cost, textbook.** The gap is only worth closing if complete data is worth something. Complete data loses to Seyfarth's complete, reviewed data at the same price of free. Finishing gets us to a better version of second-worst. |
| "The token/backfill work is already wired, it's one run away" | **Commitment-and-consistency bias.** "Almost done" is a statement about the work, not about the value. Cheap to finish ≠ worth finishing. |
| "59 tests, real invariants, we built it right" | **Craft pride.** Quality of construction is not evidence of demand. A beautifully joined cabinet nobody wants is firewood with better dovetails. |
| "It costs $0, so continuing costs nothing" | **False, and the most seductive one.** It costs $0 in dollars and 100% of a build cycle. The scarce resource here was never money — it is the team's attention, and this project has consumed seven cycles of it. Continuing has no cash cost and a total opportunity cost. |
| "Search Console might show we're indexed after all" | **Confirmation bias with a permission slip.** I already checked. Zero. The instrument was requested in the hope it would say yes. |
| "The daily loop is automated, it'll just keep improving" | **Availability bias.** It has run zero times. |
| "Nobody else publishes case-level daily federal ADA filings" | The only argument with any blood in it — see §4. But it is also **hammer-and-nail**: we have a CourtListener client, therefore the answer is a CourtListener product. The tool chose the market. |

**The clean test.** Delete the repo tonight. Tomorrow, does a single human anywhere notice,
miss it, or ask where it went? No. Not one. Not the plaintiff bar (they have Lex Machina and
Docket Alarm), not defense counsel (they have Seyfarth's report on a mailing list), not
insurers, not accessibility vendors, not a researcher. **Nobody.**

Then keep the code — it is free to keep and there is real craft in it — and stop spending
cycles on it. Those are two different decisions and they have two different answers.

---

## 3. THE HUMAN-GATE PATTERN — what the undone one-minute tasks actually tell us

You asked me not to read this as a comment on the human's diligence. Good, because it isn't
one. Here is what it is.

**First, the arithmetic nobody did.** Four cycles is roughly forty minutes of wall clock.
Two cycles is twenty. The company is treating "he didn't do it within forty minutes" as a
signal of institutional decay. It is a signal that people are slower than agents, which is
not news and not a defect.

**Second, and this is the real content:** in those forty minutes, the team never once asked
whether the gate was necessary. It optimised the gate instead. Cycle after cycle of reducing
friction — pre-wiring the token, verifying end-to-end that the string reaches all 134 pages,
writing a beautiful comment block explaining the "URL prefix vs Domain" trap. Superb work on
the *ramp*. Nobody checked whether there was a *bridge fifty metres downstream*. There was.
I walked across it in §0.2 in ninety seconds.

**Three conclusions, in ascending order of importance:**

1. **A blocked gate is a hypothesis, not a fact.** "This needs a human" was asserted, written
   into a file in confident prose, and never tested. Confident prose is how a bad assumption
   survives four cycles. The more elegantly a blocker is documented, the less likely anyone
   is to re-examine it.

2. **What the human's silence actually measures is priority — the human's, correctly held.**
   A person who will spend an hour on something that matters did not spend sixty seconds on
   this. That is not neglect; that is a revealed preference, and it is the only signal from
   outside the building this project has ever received. We asked the world for one minute of
   attention. The world, in the form of the one human who knows this project exists, declined.
   **When your total addressable market is one person and he doesn't paste the token, you
   have run a market test.** It came back negative. Read it.

3. **On "is an autonomous company that cannot act without a human viable?"** — Yes, but only
   under one condition, and stated plainly:

   > A human on the critical path is fine. **A human on the critical path of the
   > *learning loop* is fatal.**

   Paying, KYC, signing, anything legally binding — those *should* need a person, forever;
   that is not a defect, that is the leash, and this company keeps that leash by design.
   But *finding out whether anyone wants the thing* must never require one. The moment your
   only source of feedback is behind a gate you cannot open, you are not autonomous — you are
   an extremely well-tested machine for generating output nobody has evaluated. That is
   exactly what seven cycles produced.

   The fix is not "nag harder" or "reduce friction further." It is a standing rule:

   > **No project may depend on a human action to learn whether it is working. If the only
   > measurement route needs a person, that project has no measurement and ships nothing
   > further until a $0, no-human route is found or the project is frozen.**

   Under that rule, ada-docket would have been frozen — or unblocked by a `site:` query — on
   cycle two. Either outcome beats what happened.

---

## 4. THE VERDICT

### I veto continued engineering investment in ada-docket.

Note precisely what I am vetoing: **build cycles**, not the asset. Those are different, and
conflating them is how teams destroy free-to-hold options in a fit of decisiveness.

**Reasons, ranked. Every one of these is as true today as it will be on day 90 — which is
how you know they are reasons and not impatience:**

1. **Structurally $0 revenue.** No KYC → no payment rail. Traffic changes nothing. The
   company exists to make money; this cannot, at any volume, ever.
2. **Free entrenched incumbents with better data.** Seyfarth since 2013, reviewed, complete,
   ranking. We offer 30.7% of the same thing at the same price.
3. **The content cannot aggregate.** 2,618 distinct defendants across 2,705 filings; nothing
   appears 5+ times. There is no entity to rank, no hub, no compounding. The long-tail SEO
   bet was placed on content of the wrong shape, and nobody checked the shape.
4. **No user was ever named.** Not a persona, not a real person, not a job to be done. Seven
   cycles, zero named users. Everything downstream of that was decoration.

**What I am explicitly NOT killing it for:** "0 visitors." The site is four hours old. Anyone
who cites that number in the closure record is repeating the error that produced the project.

### What happens to the asset: **freeze it, don't bury it**

| Action | Do it |
|---|---|
| Further build cycles, features, polish | **Stop. Zero.** This is the veto. |
| Backfill grind / CourtListener token chase | **Stop.** Getting to 100% buys a better second-place. |
| The repo, the code, the site | **Keep. Public. Untouched.** Costs $0, and the tests and coverage model are a reusable asset. |
| `com.ada-docket.daily` launchd job | **Leave running.** It is free and unattended. |
| The "daily record" claim on every page | **One exception to the freeze, and it is not optional.** The pipeline publishes even when the fetch fails — measured today, six seconds apart. A page that says "daily" while shipping stale data is a false statement to the public, and we do not leave those live because we lost interest. Either the page states its actual last successful fetch, or the claim comes off. This is honesty maintenance, not investment. |
| `docs/legal/REVIEW-plaintiff-pages.md` finding | **Stays shelved. Permanently.** 82% of the high-count plaintiff values are bare surnames conflating distinct people. Do not revive plaintiff pages as a traffic idea later; they are a defamation surface, and the freeze must not become amnesia. |
| The 90-day rule | **Restart the clock at today's date, and rewrite the rule in cycles-and-days both.** A rule that a project can violate before lunch is not a rule. |

### The one condition that reopens it

A veto with no reopening clause is a tantrum. Here is mine — and note that it costs $0 and
needs no human, which is the standard §3 says every gate must now meet:

> **ada-docket reopens for investment only if, in a single free `site:` check, the site shows
> ≥1 indexed page AND ranks in the first two pages for any real query a practitioner would
> type — measured at 30 days from today (2026-10-04), not before.**

Thirty days, because that is roughly how long an unlinked static site needs before its
absence from the index means anything. Check it with the same ninety-second command from
§0.2. If it fails: close the repo permanently and record why. **If it passes, that still does
not authorise a build cycle** — it authorises exactly one conversation, about whether a KYC'd
payment rail exists yet. Without one, indexed or not, this is a hobby with good tests.

### The finding that outlives the project

Take two things forward, and they are worth more than the 2,638 filings:

1. **The `site:` query.** Free, instant, no human, works on every project this company will
   ever ship. "Are we in the index?" is now a solved question forever. Put it in the daily run.
2. **The rule from §3.** No project may depend on a human action to learn whether it is
   working. Adopt it, and this pattern — seven cycles of excellent engineering aimed at
   nobody, followed by a funeral held four hours after the birth — does not repeat.

I would rather this company lose ada-docket and gain those two than keep ada-docket and
learn nothing. It is the better trade by an enormous margin, and it is available right now.

---

**VETO** — stop all engineering investment in ada-docket; keep the repo and the free daily
run, fix only the false "daily" claim, and reopen for discussion no earlier than 2026-10-04
and only if a $0 `site:` check shows ≥1 indexed page *and* a KYC'd payment rail exists.
