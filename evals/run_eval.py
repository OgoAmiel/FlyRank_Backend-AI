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
    with urlopen(request, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate triage category accuracy.")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/triage/",
        help="Triage endpoint URL",
    )
    args = parser.parse_args()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    matched = 0
    failures = []

    for case in cases:
        try:
            actual = call_endpoint(args.url, case["input"])
            actual_category = actual.get("category")
            if actual_category == case["expected"]["category"]:
                matched += 1
            else:
                failures.append(
                    {
                        "id": case["id"],
                        "expected": case["expected"]["category"],
                        "actual": actual_category,
                    }
                )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append({"id": case["id"], "expected": case["expected"]["category"], "actual": str(exc)})

    total = len(cases)
    percentage = matched / total * 100 if total else 0
    print(f"Category matches: {matched}/{total} ({percentage:.1f}%)")
    print("Failures:")
    if failures:
        for failure in failures:
            print(json.dumps(failure, ensure_ascii=False))
    else:
        print("none")
    return 0 if matched == total else 1


if __name__ == "__main__":
    sys.exit(main())