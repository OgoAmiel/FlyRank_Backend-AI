import time
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, ValidationError


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_PAGE_1_URL = urljoin(
    BASE_URL,
    "catalogue/page-1.html"
)

USER_AGENT = (
    "FlyRankInternship A9/1.0 "
    "(+https://github.com/OgoAmiel/FlyRank_Backend-AI)"
)

SCRAPER_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRAPER_DIR / "cache"
OUTPUT_DIR = SCRAPER_DIR / "output"

PAGE_1_CACHE = CACHE_DIR / "catalogue-page-1.html"
BOOKS_OUTPUT_FILE = OUTPUT_DIR / "books.json"
ERRORS_OUTPUT_FILE = OUTPUT_DIR / "errors.json"
RUN_REPORT_OUTPUT_FILE = OUTPUT_DIR / "run-report.json"

REQUEST_TIMEOUT = 10
REQUEST_DELAY = 0.5

FAKE_BOOK_URL = (
    "https://books.toscrape.com/catalogue/"
    "definitely-not-a-real-book_0000/index.html"
)


# ============================================================
# SCHEMA
# ============================================================

class BookRecord(BaseModel):
    """
    Validated output record for one scraped book.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str


# ============================================================
# CACHE HELPERS
# ============================================================

def read_cached_page(cache_file: Path) -> str:
    """
    Read an already downloaded page from the local cache.
    """

    return cache_file.read_text(
        encoding="utf-8"
    )


def download_page(url: str, cache_file: Path) -> str:
    """
    Download a page from the website and save it to the cache.

    The request:
    - uses our honest User-Agent
    - has a timeout
    - checks the status code before parsing
    """

    headers = {
        "User-Agent": USER_AGENT
    }

    for attempt in range(1, 3):

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

        except requests.Timeout as error:

            if attempt == 1:
                print(
                    f"Request timed out, retrying once: "
                    f"{url}"
                )
                time.sleep(REQUEST_DELAY)
                continue

            raise RuntimeError(
                f"Request timed out after retry: {error}"
            )

        except requests.RequestException as error:
            raise RuntimeError(
                f"Request failed: {error}"
            )

        if response.status_code == 200:
            break

        if response.status_code in (403, 404):
            raise RuntimeError(
                f"Fetch failed with status code: "
                f"{response.status_code}"
            )

        if 500 <= response.status_code <= 599 and attempt == 1:
            print(
                f"Server error {response.status_code}, "
                f"retrying once: {url}"
            )
            time.sleep(REQUEST_DELAY)
            continue

        raise RuntimeError(
            f"Fetch failed with status code: "
            f"{response.status_code}"
        )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # The site headers are not reliable for charset.
    response.encoding = "utf-8"

    html = response.text

    cache_file.write_text(
        html,
        encoding="utf-8"
    )

    return html


# ============================================================
# CATALOGUE PAGE HELPERS
# ============================================================

def extract_book_links(
    html: str,
    page_url: str
) -> list[str]:
    """
    Extract all book links from a catalogue page.

    Relative URLs are converted into absolute URLs using
    urljoin().
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    book_links = []

    for article in soup.select(
        "article.product_pod"
    ):

        link = article.select_one(
            "h3 a"
        )

        if not link:
            continue

        href = link.get("href")

        if not href:
            continue

        absolute_url = urljoin(
            page_url,
            href
        )

        book_links.append(
            absolute_url
        )

    # Remove duplicates while preserving order.
    return list(
        dict.fromkeys(book_links)
    )


def find_next_page(
    html: str,
    page_url: str
) -> str | None:
    """
    Find the catalogue's own 'next' link.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    next_link = soup.select_one(
        "li.next a"
    )

    if not next_link:
        return None

    href = next_link.get("href")

    if not href:
        return None

    return urljoin(
        page_url,
        href
    )


def get_catalogue_cache_file(
    page_number: int
) -> Path:
    """
    Return the cache filename for a catalogue page.
    """

    return CACHE_DIR / (
        f"catalogue-page-{page_number}.html"
    )


# ============================================================
# CATALOGUE SCRAPER
# ============================================================

def scrape_catalogue():
    """
    Scrape the first three catalogue pages.

    Page 1 is read from the existing cache.

    Pages 2 and 3:
    - follow the site's 'next' link
    - use cache when available
    - otherwise make a real request
    - wait 0.5 seconds before real requests
    """

    all_book_links = []

    # --------------------------------------------------------
    # PAGE 1
    # --------------------------------------------------------

    print(
        "Reading page 1 from cache..."
    )

    html = read_cached_page(
        PAGE_1_CACHE
    )

    current_url = BASE_URL

    book_links = extract_book_links(
        html,
        current_url
    )

    all_book_links.extend(
        book_links
    )

    print(
        f"Page 1: found {len(book_links)} books."
    )

    # --------------------------------------------------------
    # PAGES 2 AND 3
    # --------------------------------------------------------

    for page_number in range(2, 4):

        next_url = find_next_page(
            html,
            current_url
        )

        if next_url is None:

            print(
                "No next page found. Stopping."
            )

            break

        current_url = next_url

        cache_file = get_catalogue_cache_file(
            page_number
        )

        # ----------------------------------------------------
        # USE CACHE IF AVAILABLE
        # ----------------------------------------------------

        if cache_file.exists():

            print(
                f"Reading page {page_number} "
                f"from cache..."
            )

            html = read_cached_page(
                cache_file
            )

        # ----------------------------------------------------
        # OTHERWISE MAKE A REAL REQUEST
        # ----------------------------------------------------

        else:

            print(
                f"Waiting before requesting "
                f"page {page_number}..."
            )

            time.sleep(
                REQUEST_DELAY
            )

            print(
                f"Downloading page {page_number}: "
                f"{current_url}"
            )

            html = download_page(
                current_url,
                cache_file
            )

        book_links = extract_book_links(
            html,
            current_url
        )

        all_book_links.extend(
            book_links
        )

        print(
            f"Page {page_number}: "
            f"found {len(book_links)} books."
        )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    all_book_links = list(
        dict.fromkeys(
            all_book_links
        )
    )

    print()
    print(
        "Catalogue scraping complete."
    )

    print(
        f"Total unique book links: "
        f"{len(all_book_links)}"
    )

    return all_book_links


# ============================================================
# DETAIL PAGE CACHE
# ============================================================

def get_detail_cache_file(
    book_url: str
) -> Path:
    """
    Create a safe cache filename for a book detail page.

    Example:

    a-light-in-the-attic_1000.html
    """

    filename = book_url.rstrip(
        "/"
    ).split("/")[-2]

    return CACHE_DIR / (
        f"{filename}.html"
    )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(
    element
) -> str | None:
    """
    Safely extract clean text from a BeautifulSoup element.
    """

    if element is None:
        return None

    text = element.get_text(
        " ",
        strip=True
    )

    if not text:
        return None

    return text


def normalize_price_text(
    price_text: str | None
) -> str | None:
    """
    Normalize the displayed pound price text.
    """

    if price_text is None:
        return None

    return price_text.replace(
        "Â£",
        "£"
    )


def parse_price_gbp(
    price_text: str | None
) -> float | None:
    """
    Convert a raw pound price like '£51.77' into 51.77.
    """

    if price_text is None:
        return None

    normalized = price_text.replace(
        "Â£",
        "£"
    ).replace(
        "£",
        ""
    ).replace(
        ",",
        ""
    ).strip()

    if not normalized:
        return None

    try:
        return float(normalized)
    except ValueError:
        return None


def normalize_book_record(
    raw_record: dict
) -> BookRecord:
    """
    Normalize raw scraped data into a validated record.
    """

    normalized_record = {
        **raw_record,
        "price_gbp": parse_price_gbp(
            raw_record.get("price_text")
        )
    }

    record = BookRecord.model_validate(
        normalized_record
    )

    if not record.product_url.startswith(
        "https://"
    ):
        raise ValueError(
            "product_url must start with https://"
        )

    if not record.source_page.startswith(
        "https://"
    ):
        raise ValueError(
            "source_page must start with https://"
        )

    return record


def write_json_file(
    output_file: Path,
    payload
) -> None:
    """
    Write JSON output deterministically.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )


# ============================================================
# DESCRIPTION PARSER
# ============================================================

def extract_description(
    soup: BeautifulSoup
) -> str | None:
    """
    Extract the book description from the product area.

    Books to Scrape places the description underneath
    the 'Product Description' heading.

    Some books have no description, so None is returned.
    """

    product_description = soup.select_one(
        "#product_description"
    )

    if product_description is None:
        return None

    description_parts = []

    # The actual description is normally contained in the
    # paragraph immediately following #product_description.
    description_element = (
        product_description.find_next_sibling(
            "p"
        )
    )

    if description_element is not None:

        text = clean_text(
            description_element
        )

        if text:
            description_parts.append(
                text
            )

    if not description_parts:
        return None

    description = " ".join(
        description_parts
    ).strip()

    # Remove the website's trailing "...more" marker
    # if it is present.
    if description.endswith(
        "...more"
    ):
        description = description[
            :-len("...more")
        ].rstrip()

    return description or None


# ============================================================
# RATING PARSER
# ============================================================

def extract_rating(
    product_area
) -> str | None:
    """
    Extract the rating from the product area.

    Example:

    <p class="star-rating Three">
    """

    if product_area is None:
        return None

    rating_element = product_area.select_one(
        "p.star-rating"
    )

    if rating_element is None:
        return None

    classes = rating_element.get(
        "class",
        []
    )

    for class_name in classes:

        if class_name != "star-rating":
            return class_name

    return None


# ============================================================
# AVAILABILITY PARSER
# ============================================================

def extract_availability(
    product_area
) -> str | None:
    """
    Extract availability from the product information table.

    Example:

    In stock (22 available)
    """

    if product_area is None:
        return None

    availability_row = product_area.select_one(
        "table.table-striped tr"
    )

    # Rather than trusting the first row, specifically look
    # for the row whose heading says Availability.
    for row in product_area.select(
        "table.table-striped tr"
    ):

        header = row.select_one(
            "th"
        )

        value = row.select_one(
            "td"
        )

        if header is None or value is None:
            continue

        if header.get_text(
            strip=True
        ) == "Availability":

            return clean_text(
                value
            )

    return None


# ============================================================
# PRICE PARSER
# ============================================================

def extract_price(
    product_area
) -> str | None:
    """
    Extract the price specifically from the product area.

    This avoids grabbing an unrelated price elsewhere
    on the page.
    """

    if product_area is None:
        return None

    price_element = product_area.select_one(
        "p.price_color"
    )

    return normalize_price_text(
        clean_text(
            price_element
        )
    )


# ============================================================
# DETAIL PAGE PARSER
# ============================================================

def parse_book_page(
    html: str,
    product_url: str,
    source_page: str,
    fetched_at: str
) -> dict:
    """
    Parse one book detail page and return the raw record.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # --------------------------------------------------------
    # PRODUCT AREA
    # --------------------------------------------------------
    #
    # This keeps selectors focused on the actual product
    # information rather than the entire document.
    #

    product_area = soup.select_one(
        "article.product_page"
    )

    if product_area is None:
        raise RuntimeError(
            f"Could not find product area: "
            f"{product_url}"
        )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_element = product_area.select_one(
        "div.product_main h1"
    )

    title = clean_text(
        title_element
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price_text = extract_price(
        product_area
    )

    # --------------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------------

    availability_text = extract_availability(
        product_area
    )

    # --------------------------------------------------------
    # RATING
    # --------------------------------------------------------

    rating_text = extract_rating(
        product_area
    )

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description = extract_description(
        soup
    )

    # --------------------------------------------------------
    # RETURN RAW RECORD
    # --------------------------------------------------------

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


# ============================================================
# DETAIL PAGE SCRAPER
# ============================================================

def scrape_book_details(
    book_links: list[str],
    source_pages: dict[str, str]
) -> tuple[list[dict], list[dict], dict]:
    """
    Fetch and parse every book detail page.

    Cached pages are read locally.

    Real requests:
    - use the User-Agent
    - use a timeout
    - check status code
    - wait 0.5 seconds between requests
    """

    records_by_url = {}
    errors = []
    cache_hits = 0
    pages_fetched = 0

    print()
    print(
        "Starting detail-page scraping..."
    )

    for index, book_url in enumerate(
        book_links,
        start=1
    ):

        cache_file = get_detail_cache_file(
            book_url
        )

        # ----------------------------------------------------
        # READ FROM CACHE
        # ----------------------------------------------------

        source_page = source_pages.get(
            book_url,
            CATALOGUE_PAGE_1_URL
        )

        fetched_at = datetime.now(
            timezone.utc
        ).isoformat()

        try:

            if cache_file.exists():

                print(
                    f"Reading detail page "
                    f"{index}/{len(book_links)} "
                    f"from cache..."
                )

                html = read_cached_page(
                    cache_file
                )
                cache_hits += 1

            else:

                if index > 1:

                    print(
                        "Waiting before requesting "
                        "next detail page..."
                    )

                    time.sleep(
                        REQUEST_DELAY
                    )

                print(
                    f"Downloading detail page: "
                    f"{book_url}"
                )

                html = download_page(
                    book_url,
                    cache_file
                )
                pages_fetched += 1

            raw_record = parse_book_page(
                html=html,
                product_url=book_url,
                source_page=source_page,
                fetched_at=fetched_at
            )

            validated_record = normalize_book_record(
                raw_record
            )

            records_by_url[book_url] = (
                validated_record.model_dump(
                    mode="json"
                )
            )

            print(
                f"Parsed {index}/{len(book_links)}: "
                f"{validated_record.title}"
            )

        except (
            RuntimeError,
            ValueError,
            ValidationError
        ) as error:

            errors.append({
                "product_url": book_url,
                "source_page": source_page,
                "fetched_at": fetched_at,
                "reason": str(error)
            })

            print(
                f"Skipped {index}/{len(book_links)}: "
                f"{book_url}"
            )
            print(
                f"Reason: {error}"
            )

    print()
    print(
        "Detail-page scraping complete."
    )

    print(
        f"Total raw records: "
        f"{len(records_by_url)}"
    )

    stats = {
        "pages_attempted": len(book_links),
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": len(records_by_url),
        "invalid_records": len(errors),
        "failed_pages": len(errors)
    }

    return (
        list(records_by_url.values()),
        errors,
        stats
    )


def build_run_report(
    start_epoch: float,
    started_at: str,
    stats: dict
) -> dict:
    """
    Build a run-level report with timing and counters.
    """

    duration_seconds = round(
        time.time() - start_epoch,
        3
    )

    return {
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": stats["valid_records"],
        "invalid_records": stats["invalid_records"],
        "failed_pages": stats["failed_pages"]
    }


# ============================================================
# BUILD BOOK LINKS + SOURCE PAGE MAPPING
# ============================================================

def scrape_catalogue_with_sources():
    """
    Scrape the first three catalogue pages while keeping
    track of which catalogue page each book came from.

    Returns:

        book_links
        source_pages
    """

    all_book_links = []
    source_pages = {}

    # --------------------------------------------------------
    # PAGE 1
    # --------------------------------------------------------

    print(
        "Reading page 1 from cache..."
    )

    html = read_cached_page(
        PAGE_1_CACHE
    )

    current_url = BASE_URL

    book_links = extract_book_links(
        html,
        current_url
    )

    for book_url in book_links:

        source_pages[book_url] = (
            CATALOGUE_PAGE_1_URL
        )

    all_book_links.extend(
        book_links
    )

    print(
        f"Page 1: found {len(book_links)} books."
    )

    # --------------------------------------------------------
    # PAGES 2 AND 3
    # --------------------------------------------------------

    for page_number in range(2, 4):

        next_url = find_next_page(
            html,
            current_url
        )

        if next_url is None:

            print(
                "No next page found. Stopping."
            )

            break

        current_url = next_url

        cache_file = get_catalogue_cache_file(
            page_number
        )

        if cache_file.exists():

            print(
                f"Reading page {page_number} "
                f"from cache..."
            )

            html = read_cached_page(
                cache_file
            )

        else:

            print(
                f"Waiting before requesting "
                f"page {page_number}..."
            )

            time.sleep(
                REQUEST_DELAY
            )

            print(
                f"Downloading page {page_number}: "
                f"{current_url}"
            )

            html = download_page(
                current_url,
                cache_file
            )

        book_links = extract_book_links(
            html,
            current_url
        )

        for book_url in book_links:

            source_pages[book_url] = (
                current_url
            )

        all_book_links.extend(
            book_links
        )

        print(
            f"Page {page_number}: "
            f"found {len(book_links)} books."
        )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    all_book_links = list(
        dict.fromkeys(
            all_book_links
        )
    )

    print()
    print(
        "Catalogue scraping complete."
    )

    print(
        f"Total unique book links: "
        f"{len(all_book_links)}"
    )

    return (
        all_book_links,
        source_pages
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_start_epoch = time.time()
    run_started_at = datetime.now(
        timezone.utc
    ).isoformat()

    # --------------------------------------------------------
    # STAGE 1 — CATALOGUE
    # --------------------------------------------------------

    book_links, source_pages = (
        scrape_catalogue_with_sources()
    )

    if os.getenv(
        "INJECT_FAKE_BOOK_URL"
    ) == "1":

        source_pages[FAKE_BOOK_URL] = (
            CATALOGUE_PAGE_1_URL
        )

        book_links = list(
            dict.fromkeys(
                [
                    *book_links,
                    FAKE_BOOK_URL
                ]
            )
        )

        print(
            "Injected one fake URL for failure "
            "handling checkpoint."
        )

    # --------------------------------------------------------
    # STAGE 2 — BOOK DETAIL PAGES
    # --------------------------------------------------------

    records, errors, stats = scrape_book_details(
        book_links,
        source_pages
    )

    write_json_file(
        BOOKS_OUTPUT_FILE,
        records
    )

    write_json_file(
        ERRORS_OUTPUT_FILE,
        errors
    )

    run_report = build_run_report(
        run_start_epoch,
        run_started_at,
        stats
    )

    write_json_file(
        RUN_REPORT_OUTPUT_FILE,
        run_report
    )

    # --------------------------------------------------------
    # CHECKPOINT OUTPUT
    # --------------------------------------------------------

    print()
    print(
        "First validated record:"
    )

    print(
        records[0]
    )

    print()
    print(
        f"books.json records: {len(records)}"
    )
    print(
        f"errors.json records: {len(errors)}"
    )
    print(
        f"run-report failed_pages: "
        f"{run_report['failed_pages']}"
    )