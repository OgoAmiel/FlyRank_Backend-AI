import requests
from pathlib import Path


URL = "https://toscrape.com/"

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "catalogue-page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship A9/1.0 (+https://github.com/OgoAmiel/FlyRank_Backend-AI)"
}

TIMEOUT = 10


def download_catalogue_page():
    print(f"Downloading: {URL}")

    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=TIMEOUT
        )
    except requests.RequestException as error:
        print(f"Request failed: {error}")
        return

    # Check the status code BEFORE processing the HTML
    if response.status_code != 200:
        print(f"Fetch failed. HTTP status: {response.status_code}")
        return

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    CACHE_FILE.write_text(
        response.text,
        encoding="utf-8"
    )

    print(f"Successfully downloaded page.")
    print(f"HTTP status: {response.status_code}")
    print(f"Saved to: {CACHE_FILE}")


if __name__ == "__main__":
    download_catalogue_page()