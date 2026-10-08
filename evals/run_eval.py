import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CASES_PATH = Path(__file__).with_name("cases.json")


def call_endpoint(url: str, text: str) -> dict:
    request = Request(
        url,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate AI triage category and urgency."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/triage/",
        help="Triage endpoint URL",
    )
    args = parser.parse_args()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    category_matches = 0
    urgency_matches = 0
    successful_requests = 0
    failures = []

    for case in cases:
        try:
            actual = call_endpoint(args.url, case["input"])
            successful_requests += 1

            expected_category = case["expected"]["category"]
            expected_urgency = case["expected"]["urgency"]

            actual_category = actual.get("category")
            actual_urgency = actual.get("urgency")

            if actual_category == expected_category:
                category_matches += 1
            else:
                failures.append({
                    "id": case["id"],
                    "field": "category",
                    "expected": expected_category,
                    "actual": actual_category,
                })

            if actual_urgency == expected_urgency:
                urgency_matches += 1
            else:
                failures.append({
                    "id": case["id"],
                    "field": "urgency",
                    "expected": expected_urgency,
                    "actual": actual_urgency,
                })

        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append({
                "id": case["id"],
                "field": "request",
                "error": str(exc),
            })

    total = len(cases)
    request_failures = total - successful_requests

    def percentage(matches, count):
        return matches / count * 100 if count else 0.0

    print("\n=== AI TRIAGE EVALUATION ===")
    print(f"Total cases: {total}")
    print(f"Successful requests: {successful_requests}/{total}")
    print(f"Request failures: {request_failures}")

    print(
        f"Category matches: {category_matches}/{successful_requests} "
        f"({percentage(category_matches, successful_requests):.1f}%)"
    )

    print(
        f"Urgency matches: {urgency_matches}/{successful_requests} "
        f"({percentage(urgency_matches, successful_requests):.1f}%)"
    )

    print("\nMismatches and errors:")
    if failures:
        for failure in failures:
            print(json.dumps(failure, ensure_ascii=False))
    else:
        print("none")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())