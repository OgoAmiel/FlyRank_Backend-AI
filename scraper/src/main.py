import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"

USER_AGENT = (
    "FlyRankInternship A9/1.0 "
    "(+https://github.com/OgoAmiel/FlyRank_Backend-AI)"
)

SCRAPER_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRAPER_DIR / "cache"

PAGE_1_CACHE = CACHE_DIR / "catalogue-page-1.html"


def read_cached_page(cache_file: Path) -> str:
    """Read an already downloaded page from the local cache."""
    return cache_file.read_text(encoding="utf-8")


def download_page(url: str, cache_file: Path) -> str:
    """Download a page and save it to the local cache."""

    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Request failed: {error}")

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed with status code: {response.status_code}"
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_file.write_text(
        response.text,
        encoding="utf-8"
    )

    return response.text


def extract_book_links(html: str, page_url: str) -> list[str]:
    """Extract all book links from a catalogue page."""

    soup = BeautifulSoup(html, "html.parser")

    book_links = []

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if link and link.get("href"):
            absolute_url = urljoin(page_url, link["href"])
            book_links.append(absolute_url)

    # Remove duplicates while preserving order
    return list(dict.fromkeys(book_links))


def find_next_page(html: str, page_url: str) -> str | None:
    """Find the catalogue's Next page link."""

    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if next_link and next_link.get("href"):
        return urljoin(page_url, next_link["href"])

    return None


def get_cache_file(page_number: int) -> Path:
    """Return the cache filename for a catalogue page."""

    return CACHE_DIR / f"catalogue-page-{page_number}.html"


def scrape_catalogue():
    all_book_links = []

    # ---------------------------------------
    # PAGE 1 — read from existing cache
    # ---------------------------------------

    print("Reading page 1 from cache...")

    html = read_cached_page(PAGE_1_CACHE)

    current_url = BASE_URL

    book_links = extract_book_links(
        html,
        current_url
    )

    all_book_links.extend(book_links)

    print(f"Page 1: found {len(book_links)} books.")

    # ---------------------------------------
    # PAGES 2 AND 3
    # ---------------------------------------

    for page_number in range(2, 4):

        next_url = find_next_page(
            html,
            current_url
        )

        if next_url is None:
            print("No next page found. Stopping.")
            break

        current_url = next_url

        cache_file = get_cache_file(page_number)

        # If we already cached this page, use the cache.
        if cache_file.exists():

            print(
                f"Reading page {page_number} from cache..."
            )

            html = read_cached_page(cache_file)

        else:

            # This is a real request, so wait first.
            print(
                f"Waiting before requesting page {page_number}..."
            )

            time.sleep(0.5)

            print(
                f"Downloading page {page_number}: {current_url}"
            )

            html = download_page(
                current_url,
                cache_file
            )

        book_links = extract_book_links(
            html,
            current_url
        )

        all_book_links.extend(book_links)

        print(
            f"Page {page_number}: "
            f"found {len(book_links)} books."
        )

    # ---------------------------------------
    # REMOVE DUPLICATES
    # ---------------------------------------

    all_book_links = list(
        dict.fromkeys(all_book_links)
    )

    print()
    print("Scraping complete.")
    print(f"Total unique book links: {len(all_book_links)}")

    return all_book_links


if __name__ == "__main__":
    links = scrape_catalogue()

    print()
    print("Book links:")

    for link in links:
        print(link)