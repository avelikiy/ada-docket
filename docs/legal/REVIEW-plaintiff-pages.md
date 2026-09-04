# REVIEW-plaintiff-pages — Legal Reviewer

Reviewed: `scripts/fetch.py` (HEAD, commit `9928d6b`), `scripts/build.py` (same),
`data/*.ndjson` (2,705 rows, Jan 2025–Sep 2026), live CourtListener v4 API
response for a current filing, and prior commit `885d8f5` ("firm and state
pages, and stop shipping links that 404").

Standard applied: common-law defamation / defamation-by-implication and false
light (Restatement (Second) of Torts §§ 559, 652E), FCRA "consumer report"
definition (15 U.S.C. § 1681a(d)), First Amendment public-record publication
doctrine (*Cox Broadcasting Co. v. Cohn*, 420 U.S. 469 (1975); *Florida Star v.
B.J.F.*, 491 U.S. 524 (1989); *Bartnicki v. Vopper*, 532 U.S. 514 (2001)),
aggregation/"practical obscurity" doctrine (*DOJ v. Reporters Committee for
Freedom of the Press*, 489 U.S. 749 (1989)), right-of-publicity newsworthiness
exceptions (e.g. N.Y. Civil Rights Law §§ 50–51), and this project's own prior
decision record (commit `885d8f5`).

## Scope

Reviewed the proposal to publish ~69 `/plaintiff/<slug>.html` pages, one per
named plaintiff, each headlined by a lawsuit count. Verified the claim
empirically against the live dataset rather than treating it as hypothetical.
Out of scope: general site security, CourtListener ToS compliance, and the
existing firm/court/state/month pages, which are not part of this proposal and
are addressed only for comparison.

## Data finding — the proposal's central defect is empirically confirmed, not theoretical

`scripts/fetch.py:96-97` derives `plaintiff` by splitting the case caption on
`" v. "` and keeping the left side verbatim — no first-name requirement, no
party-list cross-check, no unique identifier:

```python
out["defendant"] = name.split(" v. ")[-1].strip() if " v. " in name else ""
out["plaintiff"] = name.split(" v. ")[0].strip() if " v. " in name else ""
```

Court captions are inconsistent about whether they lead with a full name
("Dawn Stevens v. Pom Grill Corp.") or a surname alone ("Cesario v. Atelier
Luxury Group, LLC"). I queried the actual dataset:

- 2,132 of 2,705 rows (79%) have a **single-token** `plaintiff` value (a bare
  surname).
- Of the 67 plaintiff values with ≥10 filings — the exact set that would
  headline the proposed pages, per the brief's own "40+ suits" framing — **55
  (82%) are single-token surnames.**
- Cross-checking the `party` field (the full party list CourtListener returns
  per docket) against the four highest-count surnames shows they are not one
  person each:
  - `"Fernandez"` (78 filings) = at least **4 distinct people**: Felipe
    Fernandez, Devin Fernandez, Nelson Fernandez, Jacqueline Fernandez —
    filed across 4 different districts (FLMD, NYED, NYSD, FLSD).
  - `"Hernandez"` (40 filings) = at least 4 distinct people, including Jose
    Hernandez, Yudy Hernandez, Timothy Hernandez.
  - `"Williams"` (37 filings) = at least 4 distinct people.
  - `"Jackson"` (35 filings) = at least 6 distinct people, spanning LAMD,
    NYSD, ILND.

A page titled **"Fernandez — 78 ADA Title III filings"** would not describe
any single human. It would be a chimera of at least four unrelated people —
one of them, on this evidence, a woman (Jacqueline Fernandez) merged into a
count that reads as one serial filer. The flagship use case the proposal
describes ("Marcos Calcano — 40+ suits") is not a real example in the current
data (the actual Calcano entry has 4 filings, all one person) — but the
mechanism that would produce it, applied to the real top-67 list, produces
false composite dossiers 82% of the time.

This is the same failure mode the project already killed once, at higher
stakes. Commit `885d8f5` removed a defendant-grouping feature specifically
because merging on a name string is "the error that took the defendant
grouping off this site," and did so for **businesses** — entities with no
privacy interest and, per that commit's own reasoning, "acting in a public
professional capacity." Plaintiffs are private natural persons, many of them
disabled individuals whose disability is the substance of the suit. The
identity-guessing risk this project already treated as disqualifying for
corporate defendants is present here in a more severe form, against a more
protected class of subject, and — per the numbers above — occurring at a
*higher* rate than it would have for defendants.

## 1. Defamation / false-light exposure from a wrong per-person count

Confirmed real, not theoretical, given the data above. The tort mechanism:

- **Defamation by implication / false light** does not require the underlying
  individual facts to be false — it requires the *overall impression* created
  by their arrangement to be false and harmful. A page stating "Fernandez has
  filed 78 ADA Title III lawsuits" creates a specific, checkable, false
  impression: that Jacqueline Fernandez (or any of the other three real
  Fernandezes in the set) is a 78-suit serial filer. Each is party to only a
  fraction of that count, and the page does not merely fail to say so — its
  entire framing (one name, one page, one number) asserts the opposite.
- **"Serial ADA plaintiff" is a loaded characterization.** Defense-side
  advocacy groups already compile and publicize "professional plaintiff"
  lists as an adversarial tactic in ADA litigation; being placed on such a
  list has real reputational and litigation consequences (opposing counsel
  cites it to argue lack of standing / bad faith). A wrongly-merged count is
  not a harmless data error here — it hands a specific, wrong, weaponizable
  number to whoever is opposing that plaintiff's *next* suit.
- **Exposure if even one record on a person's page is wrong:** on a single-item
  page (most of the site's existing rows), one wrong entry is a data-quality
  footnote. On a plaintiff page, one wrong entry is the entire editorial
  claim — the page's reason to exist is the count, and the count is the false
  statement. This is qualitatively different from the wrong-suit-nature-code
  defect fixed earlier (which affected which suits appeared, not who a suit
  is asserted to belong to).
- **Operator exposure:** this is a $0 solo project, no entity, no insurance.
  A defamation/false-light claim (or even a credible cease-and-desist from a
  plaintiff's attorney, who will recognize this exact fact pattern
  immediately) is aimed at an individual with no liability shield. That is
  the real-world risk this review is asked to weigh, not a hypothetical one.

## 2. Anti-doxxing statutes / right of publicity

- **Anti-doxxing statutes** (e.g., Cal. Penal Code § 653.2, various state
  harassment-adjacent doxxing laws) generally require intent to enable
  harassment or a direct threat nexus, and target private/sensitive
  information (address, SSN, etc.), not litigation records already public
  and already published elsewhere on this same site. **Low risk** as
  currently scoped — the proposal doesn't add new categories of sensitive
  data, only a new aggregation.
- **Right of publicity** (name/likeness used in commerce or advertising) is
  **low risk** here: the site carries no ads, no paywall, no product sold
  under the plaintiff's name, and reporting on public litigation is
  news/public-interest content, which is the standard statutory exemption
  (e.g., N.Y. Civil Rights Law §§ 50–51's newsworthiness carve-out). Using a
  name as a URL slug and page title for factual reporting is not the kind of
  "use in trade" these statutes reach, *provided the content is accurate.*
  If it is not accurate (see §1), the operative claim reverts to defamation,
  not right of publicity.

## 3. Does "public record" defeat these claims? The aggregation question

No — and the site's own architecture already demonstrates why the project's
authors understand this distinction, because they apply it correctly
elsewhere and would be inconsistent to ignore it here.

- **The underlying facts are already public and already published on this
  site.** Every plaintiff name in this proposal already appears in the
  index, court, month, and state tables (`scripts/build.py`, `table()`,
  column `c-plaintiff`). Republishing a true, individual court record is
  protected: *Cox Broadcasting*, *Florida Star*, and *Bartnicki* all hold
  that truthful publication of lawfully obtained information on a matter of
  public concern is protected even against a state privacy-tort claim.
  **That protection is not in question and this review does not dispute it.**
- **What changes with a dedicated per-person page is not the facts — it's
  discoverability and framing, and both are legally material.** The site's
  `robots.txt` (`Allow: /`) and generated `sitemap.xml` mean every new page
  is indexed. Today, "Jacqueline Fernandez" does not rank for an ADA-lawsuit
  search because her one filing is one row among 2,705 in a sortable table.
  A page titled `/plaintiff/fernandez.html`, canonicalized, sitemapped, and
  headlined "78 filings," is built specifically to rank for searches of that
  surname — that is the entire stated purpose of a person page. This is
  exactly the harm the Supreme Court recognized in *DOJ v. Reporters
  Committee* under the label "practical obscurity": individually public
  records lose a real, legally cognizable privacy interest when someone
  assembles them into a single, easily retrievable dossier keyed to a name,
  even though no single record in the compilation was itself secret.
  *Reporters Committee* is a FOIA Exemption 7(C) case against a government
  agency, not a tort case against a private publisher, so it is persuasive
  reasoning, not binding law here — but state courts applying the privacy
  torts (intrusion, publicity given to private life) routinely import the
  same logic when weighing aggregation, and it directly answers the
  "compiled dossier vs. underlying record" question this review was asked to
  address: **yes, a compiled dossier is treated differently, because it
  is different in kind, not just degree.**
- **FCRA.** The site's own disclaimer (`scripts/build.py`, `DISCLAIMER`
  constant) already states it is "not a consumer report under the Fair
  Credit Reporting Act... Do not use it... to make a decision about any
  individual's... eligibility for anything." That disclaimer is necessary
  but not sufficient: FCRA's "consumer report" test in 15 U.S.C. § 1681a(d)
  turns on whether information is collected/used, or **reasonably expected
  to be used**, to evaluate eligibility for credit, insurance, employment,
  or tenancy — not on the publisher's stated intent. A per-person page
  headlined by a litigation-frequency count is precisely the kind of
  screening signal tenant-screening and insurance-underwriting products are
  built on, and regulators have pursued screening companies under FCRA for
  treating scraped court records as consumer-report inputs regardless of a
  disclaimer on the source site. The disclaimer lowers exposure; it does not
  eliminate it, and a prominent "N lawsuits" number is the single highest-risk
  element to add from an FCRA-functional standpoint — more than the existing
  per-row table entries, because it is a pre-computed *score*, not a raw record.

## 4. Plaintiff-identity ambiguity — the load-bearing defect

Covered in detail above with data. Summary of what the site would be
asserting if it merges by string match: **that a specific named person filed
every suit under that string**, when the string is frequently a bare surname
shared by unrelated people (confirmed for 4 of the top 4 surnames checked,
likely most of the remaining 51 single-token entries in the ≥10-filing set).
Splitting instead of merging does not solve it either — the same real person
can appear as "Fernandez" in one caption and "Felipe Fernandez" in another,
which would produce two separate, incomplete, and misleadingly *low* pages
for one real person, which is a lesser but still real accuracy defect (an
undercount is not defamatory the way an overcount/merge is, but it is still
a factual claim the site cannot currently stand behind).

The live CourtListener v4 API does return a `party_id` array parallel to
`party` (confirmed by direct query on 2026-09-04), which `scripts/fetch.py`'s
`KEEP` tuple does not currently capture. This is a **potential** path to a
real identity key, but it is unverified: CourtListener/RECAP is not known to
guarantee that `party_id` resolves to one canonical ID per real person across
separate dockets (PACER itself has no cross-district person ID; each RECAP
docket's Party rows are commonly created independently per case). Building
identity matching on an assumption about a field this project has not
inspected, on a data source whose own documentation does not state the
guarantee needed, repeats the exact mistake being reviewed.

## 5. Section 230

**Not applicable, and not in the site's favor.** Section 230 immunizes
platforms for *third-party* content they host but did not create. This site
is not hosting third-party submissions — `scripts/fetch.py` pulls raw
CourtListener data and `scripts/build.py` computes and publishes derived
facts (the plaintiff string, the count, the page framing) that do not exist
in that form in the source. The count and the page are the operator's own
editorial output built from raw material, which is precisely the kind of
"development" of information that forfeits 230 treatment even where 230
would otherwise apply. The operator is the publisher of the plaintiff pages
in the plain sense of that word, and bears publisher liability for what they
assert, not just for what they mirror.

## 6. Serial-filer politics and state vexatious-litigant statutes

CA, FL, and NY vexatious-litigant / high-frequency-litigant provisions
constrain *courts'* handling of repeat filers (e.g., pre-filing review
requirements); they are not a safe harbor for a third party to publish a
private compilation of someone's filing count, and they do not shift any
burden onto the subject to correct a wrong compilation. If anything, the
existence of these statutes raises the stakes: it confirms that "how many
ADA suits has X filed" is a legally and politically consequential number
that courts themselves handle through a formal, cross-checked process before
attaching consequences to it — which is a strong argument that a hobby
project doing the same attribution informally, and by surname string match,
should not publish it as a headline fact.

## Verdict

**NO-GO** on the proposal as specified (per-plaintiff pages built by merging
the current `plaintiff` string field).

The defect is not a hypothetical risk to be mitigated with a disclaimer — it
is a measured fact about the current dataset: 82% of the pages the feature
would headline merge multiple real, unrelated people under one name and one
false count. This project already made the correct call on the identical
failure mode for a lower-stakes subject (business defendants, commit
`885d8f5`) and should not reverse that judgment for private individuals,
several of whom are disabled by definition of the suits being tracked, with
no entity or insurance behind the operator to absorb the resulting claim.

### What would have to be true before this is revisited (not a ship list — a research list)

1. A per-person identity key must exist and be verified, not assumed.
   Query CourtListener's `party_id` (and/or a `/parties/` endpoint if one
   exists) across multiple dockets for a sample of known-duplicate surnames
   (Fernandez, Hernandez, Williams, Jackson — already identified) and confirm
   whether the same real person gets the same `party_id` across cases, and
   whether different real people sharing a name get different IDs. If FLP
   cannot confirm this guarantee, the field cannot be used as a match key.
2. If no reliable ID exists, matching must require full given-name +
   surname agreement at minimum, AND a secondary corroborating signal
   (same attorney/firm across filings, or manual confirmation) before two
   filings are treated as the same person — string equality on a full name
   alone is insufficient given confirmed same-name/different-person
   collisions even among two-token names in this dataset (e.g. two distinct
   "Jose Hernandez" entries were observed).
3. Any row whose identity cannot be confirmed to the standard in (2) must be
   excluded from a plaintiff page, not defaulted into the largest matching
   bucket. A page with 4 confirmed filings and an explicit "N other
   filings could not be confidently attributed to this person" note is
   defensible; a page that silently merges is not.
4. The page must not be built around a bare "N lawsuits" headline number as
   its primary framing. If shipped, the page states individual filings with
   dates, courts, and docket links — the same list format already used
   elsewhere on the site — without a synthesized aggregate count as the
   page's title-level claim, since the count is the specific statement this
   review finds indefensible at current data quality.
5. `robots.txt` / sitemap inclusion for any plaintiff page must be an
   explicit, separate decision from shipping the page at all — not
   inherited automatically from the site-wide `Allow: /`. Practical
   obscurity is a real mitigant; removing it should be a conscious choice
   made after (1)–(4) are satisfied, not a side effect of the existing
   crawl policy.
6. A visible correction/removal path must exist and be tested before launch
   — a named individual who finds themselves misattributed needs a faster
   remedy than a GitHub issue on a repo they don't know exists. At minimum:
   a stated contact method on every plaintiff page, and a documented
   turnaround commitment.
7. Counsel/firm-level identity (already shipped) is not a precedent that
   generalizes here and should not be cited as one. Firms are business
   entities filing in a professional capacity with no privacy interest in
   the fact of representation; that is the entire basis on which `885d8f5`
   distinguished firm pages from defendant pages. Plaintiffs are the
   opposite case on both axes (private individuals, no professional-capacity
   framing) and inherit neither precedent.

## Strongest argument against this verdict

The site already publishes every one of these facts today, one row at a
time, fully indexed, fully attributed by the same ambiguous `plaintiff`
string, on the index/court/month/state pages — the identity-collision defect
identified here (single-token surnames merging distinct people) is **already
live on the production site**, just distributed across many pages instead of
concentrated on one. A determined reader can already reconstruct "how many
suits has this surname filed" by using the site's own search box (visible in
`table()`'s `<input id="q">`) against the surname. If the underlying defect is
tolerable in its current, already-shipped distributed form, the argument that
concentrating it onto one page crosses a bright line is a matter of degree,
not of kind — and a project already carrying that distributed risk gains
comparatively little additional exposure by making it easier to find, while
losing real research and journalistic utility ("who are the serial filers in
this district" is a legitimate public-interest question this site otherwise
answers well). Under this view the correct fix is the same in both cases —
capture and use a real identity key — and blocking only the aggregated page
while leaving the distributed version live treats the presentation, not the
underlying data defect, as the harm.

VERDICT: NO-GO reason="82% of the pages the feature would headline (55 of 67
plaintiffs with >=10 filings) merge multiple confirmed distinct real people
under one surname and one false lawsuit count (Fernandez=4 people, Jackson=6
people, verified against the party field); this repeats, at higher stakes
against private individuals, the identity-guessing failure the project
already reversed for business defendants in commit 885d8f5. Revisit only per
the 7-item research list above."
