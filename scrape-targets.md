# Scrape targets: interim / zzp test automation (NL market or fully remote)

Compiled 2026-09-21. Basis: 50 web searches (web_search_fast) plus Sid Boedhoe's email "Bedankt" (2025-03-05).

Read this first:
- Sid's 14 sites were fetched on 2026-09-21 (after the URLs were pasted into chat). Everything in section 1 is from those fetches. Section 2 and 3 are still search snippets only: verify before building on them.
- A fetch shows what a logged-out, non-JavaScript client gets. Several sites render listings client-side, so "no listings visible" means "not in the static HTML", not "empty".
- Rate context: NL zzp test automation is about EUR 60-100/h (detransparantebroker.nl). International remote B2B boards show far lower numbers (Netguru senior QA freelance: 32-43 USD/h; Upvanta Java/Playwright: 186-253 USD/day on justjoin.it).

## 1. Sid's list (14), fetched 2026-09-21

| # | Site | What the fetch showed | Scrapability |
|---|------|----------------------|--------------|
| 1 | circle8 VMS (circle8.my.site.com/vms) | Salesforce Experience Cloud login page. Fetch returned a "CSS Error" stub, no listings. circle8 is a DICTU framework supplier (Oct 2024). | Login. Not scrapable without credentials. |
| 2 | pro-act.nl/vacatures | Pro-Act IT, Haarlem. 14 assignments listed, each with title and hours/week only. Detail pages at /vacatures/<slug>-<id>/ (IDs 8681-8877). Mixed IT and non-IT (project manager, PMO, Qlik, Azure, developer, applicatiebeheer). Clients: education, healthcare, government, corporate. No test roles in the 14. | Public static HTML. Easy. |
| 3 | hero.eu/interim-opdrachten | Hero Interim Professionals. Sid's interimprofessionals.hero.eu now redirects to hero.eu, and the old /en/aanvraag/... URLs I saw in search are a different scheme. 36 assignments (ICT & Data 18). Filters: sector, hours, region (Randstad 28), work location. Work-location values are only "Hybride (50/50)" 12, "Hybride in overleg" 13, "Op locatie" 5. No remote value. Each item has date, sector, city, hours/week. Detail URL: /interim-opdrachten/<slug>-<8 hex>. No test roles in the 36. | Public, server-rendered list. Easy. Old URL patterns are dead. |
| 4 | sevenstars.nl/opdrachten | Fetch refused: robots.txt disallows automated access. | Blocked by robots.txt. |
| 5 | synprofs.nl/opdrachten | Landing page, no assignment list in the fetched HTML. Sign-up for zzp'ers and suppliers. Framework contracts with many ministries (Buitenlandse Zaken, EZK, LNV, DICTU, IND, DT&V, COA, Justis, NFI, Defensie, IenW/Rijkswaterstaat, KNMI, AZ, Financien, BZK, Logius, SSC-ICT). Per-client pages exist (e.g. /opdrachtgever/dictu/). | Listings not in static HTML. Check the client pages or the network calls. |
| 6 | flexvalue.nl | Homepage only. The real listing is aanvragen.flexvalue.nl/careers/6605 (CATS ATS portal): 15 assignments, mostly Den Haag and Apeldoorn, each with a deadline. Job URL: /careers/6605/jobs/<id>-<slug>. No test roles in the 15. | Public static list on aanvragen.flexvalue.nl. Easy. |
| 7 | headfirst.nl/zelfstandig-professionals | Marketing page. It sends professionals to the Striive platform (free account at login.striive.com). The list at headfirst.nl/vind-opdrachten shows "Alle (94)" assignments with client and city (Belastingdienst ICT, Ministerie EZ HR, Kennisnet, Nationaal Archief via Cegeka), loaded client-side. Only the first 10 came through the fetch, none test roles. | Titles look public but load via JavaScript. Details are on Striive (login). |
| 8 | circle8.nl/opdrachten | Fetch refused: robots.txt disallows automated access. | Blocked by robots.txt. |
| 9 | overheidsopdrachten.nl | Single-page app. Fetch returned only "An error has occurred. This application may no longer respond until reloaded." | Needs a real browser. Unknown what it lists. |
| 10 | mijn.freelance.nl/opdracht-vinden/zoeken | Redirects to /inloggen. Public listing pages exist on www.freelance.nl/opdracht/<id>-<slug> (title, dates, hours, location, sometimes rate; full text gated). | Search is login-only. Public listing pages are scrapable. |
| 11 | onestopsourcing.esdnext.com | esd.next single-page app, "You need to enable JavaScript". | Login and JavaScript. |
| 12 | harveynash.nl/vacatures | Recruiter site. The list is client-side; the static page said "Sorry, we konden geen vacatures vinden" (search form only). Harvey Nash assignments also appear on freelance.nl. One JIO listing there said "Geen ZZP, enkel detachering". | Needs a real browser or the underlying API. |
| 13 | tender-link.nl | Government and semi-government assignments only. Each assignment is open as zzp, detachering, or both, and every zzp assignment is pre-screened for Wet DBA. Rate or gross salary indication shown per assignment. Margin 10% on zzp and 15% on detachering, added on top of your rate. Apply by web form, no account. URLs: /freelance-opdrachten/<province>/, /detachering-opdrachten/<province>/, /functierol/<role>-vacatures/. Job alerts. The listing items were not in the static HTML. | Public. The zzp/detachering split makes it the best fit for Sid's "interim or zzp only" request. |
| 14 | stone-interim.nl/opdrachten | Only page metadata came back (Finance, HR, IT, Technology). Listing is client-rendered. | Needs a real browser. |

Cross-site finding: the same requests are posted on several bureaus. Belastingdienst ICT roles (Automatiserings/Gen-AI expert, BackStage Engineers, Full Stack Developer/DevOps) appear on both FlexValue and HeadFirst. "Analist Operational Excellence" and "Senior Azure Operations Engineer" appear on both Pro-Act and Hero. A scraper needs dedupe on title plus client plus location.

Snapshot finding: none of the 65 listings I could read in full (Hero 36, Pro-Act 14, FlexValue 15) was a test or QA role. This is one day's snapshot, but it suggests test-automation assignments are rare on these sources.

## 2. New candidates

### A. Netherlands market

| Site | What it is | Access | Notes |
|------|-----------|--------|-------|
| TenderNed (tenderned.nl) | Official NL procurement register | Public | Shows ICT hiring frameworks and awards (e.g. Wigo4it "Inhuur ICT-professionals", TN-579779, Apr 2026; Universiteit Twente "Inhuur IT (Broker)", TN-574421, Mar 2026). Brokers bid, not individual zzp. Use it to find which bureaus to scrape. |
| DICTU framework suppliers (Oct 2024) | LINKIT/Bartosz/DiVetro consortium, Cimsolutions & SLTN, Headfirst, Circle8, Synprofs, Sogeti Nederland, Caesar Accounts, ItaQ | Their own sites | Brokers, not boards. Their vacancy pages are the scrape targets. Headfirst, Circle8 and Synprofs are covered in section 1; the rest are unchecked. |
| Other NL government frameworks | Den Haag (Dec 2024 / Jan 2025): LINKIT/DiVetro/Bartosz/Cuccibu consortium, HintTech Staffing. CJIB (2021): Between Staffing, CGI, Alten, Corebase, Devoteam, IT Topdogs. | Their own sites | Same caveat. IT-Staffing Groep describes itself as the largest detacheerder of independent ICT'ers (2,400 freelancers, advertorial, undated). |
| Jobbird (jobbird.com) | NL job board with zzp/freelance listings | Public | Seen: "freelance projectleider ... 24 uur zzp" (gemeente, hybrid). Mixed with permanent roles. |
| Malt, Jellow | Profile-based marketplaces | Profile required | Qonto names Freelance.nl, Jellow and Malt as the three big generic NL platforms. Malt draws international clients. No public assignment feed that I know of. Unverified. |
| Planet Interim | Interim professionals platform | Membership from about EUR 30, then free basic (per zzp-nederland.nl) | Manager-heavy. Weak fit for test automation. |
| Fring (Ede) | NL freelance platform for digital, data and security | ? | Founded 2019 (CB Insights). Thin evidence. |
| ICTerGezocht.nl | Dutch IT job board | ? | Listed by Manatal as a specialist IT board. Unclear if it carries freelance work. |
| IamExpat Jobs | English-language NL job board | Public | Some freelance IT roles seen (SAP O2C, Utrecht). |

### B. EU / remote boards

| Site | What it is | Access | Notes |
|------|-----------|--------|-------|
| justjoin.it | EU tech board, remote and B2B filters, salary shown | Public | About 690 testing offers. Many are tied to Polish locations even when remote. |
| Jobgether | Remote aggregator (Europe or anywhere) posting for partner companies | Public | Contract QA roles exist (e.g. YLD "Contract QA Engineer", EU). |
| WeAreDevelopers | EU developer job board | Public | About 5.5k remote or hybrid Java jobs in the EU. |
| Djinni | Remote / EU tech board | ? | Seen: QA automation, "Full Remote, EU". Ukraine-leaning. |
| Remotive | Remote board | Public | QA category; some posts restricted to Europe. |
| Nodesk | Remote board | Public | QA page and Europe page. |
| Working Nomads | Remote board | Public | Automation and Europe pages. |
| Arbeitnow | Germany-based board, English and remote tags | Public | |
| Remote OK | Global remote board | Public | Page advertises JSON and RSS feeds. US-heavy. |
| TestDevJobs | QA-only board and newsletter | Public | Regional split (Europe: 108 companies; Worldwide: 30+). |
| freelance.de, freelancermap | German freelance project boards | Free registration to apply | Remote test-automation and SDET projects seen (e.g. Playwright/Java, Android). DACH-oriented. |
| Testlio | QA freelance network | Apply / account | EMEA and global remote roles. Some region-locked (LatAm seen). Pay model unverified. |

### C. Vetted or bidding marketplaces (apply-based, no feed to scrape)

| Site | Notes |
|------|-------|
| Toptal | Vetted network, QA testers category. |
| Arc.dev | Vetted remote developers, Europe freelance, Playwright developers listed. |
| Lemon.io | Vetted EU / LatAm developers for startups. |
| Twine (twine.net) | Has an NL QA page; claims 14,500 QA engineers. |
| Upwork, Freelancer.com, Guru, Contra | Open bidding, global price competition. |
| YunoJuno | UK-oriented vetted marketplace (150k freelancers, right-to-work checks). Likely UK only. |

## 3. Checked and dropped

- Crowdtesting (uTest, test IO, Tester Work): pay per bug. Tester Work standard payout is $2-8 per bug, $10/h for test-case execution.
- itjobswatch, Dice, Virtual Vocations: the remote roles seen were UK-only or US-only.
- Wellfound: startup roles, India/US-heavy in what I saw.
- FlexJobs: paid, hand-screened.
- Inhuurdesk Politie DAS (ICT category): a TenderNed notice dated 2026-03-10 says the DAS has ended.
- WerkenInFriesland / WerkenInGelderland DAS: only 2016-2017 documents found. Status unknown.
- Randstad, Michael Page NL, YoungCapital NEXT: mostly employed or detachering roles. One Randstad listing said "ZZP is niet toegestaan".
- Indeed, Nationale Vacaturebank, LinkedIn: generic (LinkedIn is already scraped).

## 4. Scraper notes

- Exclusion keywords for the permanent/detachering noise Sid complained about (2025-03-16): "geen zzp", "zzp niet toegestaan", "enkel detachering", "in loondienst".
- A gemeente tender allows zzp'ers only when the client states the work is DBA-compliant. Absence of that statement means detachering only.
- Market context: Intelligence Group (via Consultancy.nl and ANP, Apr 2025) reported flex/zzp assignments down 33% in Q1 2025 (-45.7% in March), with detachering gaining share because the public sector prefers it. Expect a lower zzp share on government-facing sources.
- Freelance.nl gates full descriptions behind login, so a logged-out scraper only gets title, dates, hours, location and sometimes a rate.
- robots.txt: sevenstars.nl and circle8.nl disallow automated access (the fetch tool refused them). A scraper should honour that or ask Sid to request access.
- Dedupe across bureaus (same request, several agencies). Match on normalised title, end client and city.
- Rendering: Hero, Pro-Act and aanvragen.flexvalue.nl are plain HTML. Tender-Link, HeadFirst, Harvey Nash, Stone, overheidsopdrachten.nl and OneStopSourcing need a browser or their backing API.
- Tender-Link exposes zzp vs detachering per assignment, which directly answers Sid's request to drop permanent and detachering-only roles.
