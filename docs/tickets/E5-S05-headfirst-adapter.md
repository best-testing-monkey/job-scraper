# E5-S05: HeadFirst site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`,
`E1-S01`. Style reference: `job_scraper/sites/pro_act.py` for the overall
class shape, but the extraction mechanism here is different (JSON embedded
in script tags, not CSS selectors) — read this whole ticket before
starting, it's the most unusual of the adapters in this project.

## Goal

A `SiteAdapter` for headfirst.nl (`site_id = "headfirst"`,
`base_url = "https://www.headfirst.nl"`, `fetch_strategy =
FetchStrategy.STATIC`). **Known, accepted scope limits** (don't try to
solve these — they're documented gaps, not bugs to fix):
1. Only ~10 of the site's ~93 live postings are reachable via plain HTTP
   (the rest need a real browser to paginate past page 1 — no URL
   parameter works). This adapter only surfaces those ~10.
2. The full HTML job description is NOT extracted — it exists on the page
   but resolving it requires cross-referencing separate React Server
   Component chunks by a numeric ID, which is fragile and out of scope.
   Set `description` to `""` and set `scrape_note` to something like
   `"Full description not extracted — see headfirst.nl or the broker_url
   for details."` for every posting from this adapter.
3. There is no separate detail page/URL for a HeadFirst posting on
   headfirst.nl itself — applying goes through Striive (login required,
   out of scope). Set `source_url`/`stub.detail_url` to the LISTING page
   URL itself (`self.LISTING_URL`) for every posting, since that's the
   only real URL that exists.

## Context

Create: `job_scraper/sites/headfirst.py`, `tests/test_headfirst.py`.

Fixture (read-only, real data — image blobs replaced with a placeholder
string, all real job JSON/text untouched):
- `tests/fixtures/headfirst/listing.html`

`fetch_page` returns raw bytes; decode with `.decode("utf-8")` before doing
text/regex work on it (the extraction here is on decoded text, not HTML
DOM — there's no CSS selector step for the job data itself).

## Extraction algorithm

The page embeds job data as JSON inside Next.js React Server Component
script chunks: `<script>self.__next_f.push([1,"<escaped-json-string>"])</script>`,
repeated ~96 times in the page. Each chunk's payload, once unescaped, is a
string of the form `<hex-id>:<content>` — most aren't relevant; the one you
want contains the literal substring `"entity":"job_request"`.

```python
import re, json

def _unescape_chunk(raw: str) -> str:
    # raw is the text captured between the outer quotes of
    # self.__next_f.push([1,"..."]) — it's JSON-string-escaped, so
    # wrapping it in quotes and running it through json.loads correctly
    # un-escapes \", \\, \n, etc. (more reliable than manual str.replace).
    return json.loads('"' + raw + '"')

def _find_job_chunk(html_text: str) -> str | None:
    for raw in re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html_text, re.DOTALL):
        unescaped = _unescape_chunk(raw)
        if '"entity":"job_request"' in unescaped:
            return unescaped
    return None
```

Within that unescaped chunk text, each job is a JSON object starting at
`{"id":"<uuid>","status":...,"title":...,...,"entity":"job_request",...}`.
Extract every such object with a **balanced-brace scan** (don't use a
greedy/non-greedy regex for the whole object — the objects are deeply
nested and a regex will either under- or over-match): find each
`{"id":"` occurrence that's followed eventually by `"entity":"job_request"`
before the matching closing brace, then scan forward counting `{`/`}` to
find where that specific object ends. A helper like this works:

```python
def _extract_json_objects_starting_with(text: str, marker: str) -> list[dict]:
    """Find every '{' that starts an object whose text contains `marker`
    before its matching '}', by brace-counting from each candidate start."""
    results = []
    for m in re.finditer(re.escape(marker), text):
        # scan backward from marker to the nearest unmatched-so-far '{'
        start = text.rfind('{"id":"', 0, m.start())
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if obj not in results:
                            results.append(obj)
                    except json.JSONDecodeError:
                        pass
                    break
    return results
```

(Adjust as needed once you're looking at the real fixture — this is a
starting point, not a guarantee; the important part is balanced-brace
scanning, not the exact helper shape.)

Each resulting job dict has (verified real keys):
```
id                  -> use as listing_id
title               -> title
hoursPerWeekMin / hoursPerWeekMax  -> hours, formatted "MIN-MAX" (e.g. "32-36")
startDate / endDate -> duration, formatted "START - END" (just the date
                        part before "T", e.g. "2026-10-11 - 2027-04-10")
location            -> location
clientName          -> client
publishedDate       -> posted_date
referenceCode       -> store in extra_fields["referenceCode"]
brokerUrl           -> store in extra_fields["apply_url"] (Striive link,
                        useful even though full application needs login)
```

`category` and `rate` are not present as structured fields on this
site — leave both `None`.

## Acceptance criteria

- `HeadfirstAdapter.site_id == "headfirst"`, `fetch_strategy ==
  FetchStrategy.STATIC`.
- `list_postings()` given the fixture yields roughly 10 stubs (whatever
  the real fixture actually contains — assert `len(stubs) >= 5` rather
  than an exact count, since this is inherently a partial/best-effort
  source), each with `detail_url == HeadfirstAdapter.LISTING_URL` (same
  URL for every stub, per the "no real detail page" scope note above).
- At least one stub has `listing_id ==
  "28ed2087-a156-462e-b89c-fccc6ff74a71"`.
- `parse_detail()` for that stub returns a `JobPosting` with:
  `title == "Data Engineer (Medior) - RVO"`,
  `listing_id == "28ed2087-a156-462e-b89c-fccc6ff74a71"`,
  `site_id == "headfirst"`, `client == "Ministerie van Economische Zaken"`,
  `location == "Utrecht"`, `hours == "32-36"`,
  `extra_fields.get("referenceCode") == "SAISAE000050"`,
  `description == ""`, `scrape_note` is non-empty (per scope note 2
  above), `category is None`, `rate is None`.
- No live network calls in tests.

## Definition of done

Per Appendix A.
