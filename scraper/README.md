# Books to Scrape — Stage 4 Scraper

## Target Classification (Stage 0)

- Target: https://books.toscrape.com/
- Classification: public, unauthenticated HTML pages in a practice sandbox explicitly intended for scraping exercises.
- Crawl scope: first 3 catalogue pages only.

## Lane and Setup

This project runs in the Python lane.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run command (copy/paste):

```bash
python src/main.py
```

## Output Files

- `output/books.json`: validated, normalized records only.
- `output/errors.json`: per-page failures with reasons.
- `output/run-report.json`: run-level counters and timing.

## Record Schema (Pydantic)

Each stored record matches this shape:

```python
{
	"title": str,
	"product_url": str,          # canonical identity URL
	"price_text": str,           # original display value, e.g. "£51.77"
	"price_gbp": float,          # normalized numeric value, e.g. 51.77
	"availability_text": str,
	"rating_text": str,
	"description": str | None,   # optional
	"source_page": str,
	"fetched_at": str
}
```

Validation behavior:

- Every record is validated before being written to `output/books.json`.
- Invalid records are excluded from `output/books.json` and written to `output/errors.json` with a `reason`.
- Record identity is `product_url`, so duplicate URLs collapse to one record (idempotent reruns).

## Politeness Rules Implemented

- User-Agent header is sent on every network request.
- Delay between real requests: 0.5 seconds.
- Request timeout: 10 seconds.
- Local cache-first behavior for catalogue and detail pages.
- Retry policy: retry once on timeout and server errors (5xx), no retry for 403/404.

## Proof: Real Run Report

Contents of `output/run-report.json` from a real run:

```json
{
	"started_at": "2026-08-23T09:36:47.127269+00:00",
	"duration_seconds": 3.602,
	"pages_fetched": 0,
	"cache_hits": 60,
	"valid_records": 60,
	"invalid_records": 0,
	"failed_pages": 0
}
```

Why this assignment needed no browser:

The required data is already present in the server-returned HTML, so using a browser engine would add cost and complexity without improving extraction accuracy.

## One Honest Limitation

This scraper intentionally processes only the first three catalogue pages and does not crawl the full site.

## Ethics Note

Use an official API whenever one exists. Never bypass logins, paywalls, or access controls. Collect only the data needed for the task, and keep request volume low to avoid unnecessary load.