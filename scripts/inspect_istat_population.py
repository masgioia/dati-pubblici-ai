"""Inspect the official ISTAT SDMX population dataset and report its schema.

Run from the repository root:
    python scripts/inspect_istat_population.py

The request is deliberately limited to a small period. ISTAT's current
EsploraDati endpoint has been reported to return an extra year for endPeriod;
we therefore request through 2023 and keep the returned response as evidence
rather than silently assuming the time filter is correct.
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://esploradati.istat.it/SDMXWS/rest/data/IT1,22_289/A..JAN.9.TOTAL.99/"
PARAMS = {"startPeriod": "2023", "endPeriod": "2023"}
ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"


def main() -> int:
    url = f"{BASE_URL}?{urllib.parse.urlencode(PARAMS)}"
    request = urllib.request.Request(
        url,
        headers={"Accept": ACCEPT, "User-Agent": "dati-pubblici-ai/0.1 (portfolio project)"},
    )
    print(f"Source: {url}")
    print("Requesting a limited slice of the official ISTAT dataset...")

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8-sig")
            print(f"HTTP status: {response.status}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
        print(f"ERROR: ISTAT request failed: {exc}", file=sys.stderr)
        return 1

    if not body.strip():
        print("ERROR: ISTAT returned an empty response.", file=sys.stderr)
        return 2

    reader = csv.DictReader(io.StringIO(body))
    fields = reader.fieldnames or []
    if not fields:
        print("ERROR: response is not a CSV with a header row.", file=sys.stderr)
        print(body[:500], file=sys.stderr)
        return 3

    rows = list(reader)
    print(f"Columns ({len(fields)}): {', '.join(fields)}")
    print(f"Rows received: {len(rows)}")
    if not rows:
        print("No observations returned. Check endpoint/query parameters.")
        return 4

    for i, row in enumerate(rows[:5], start=1):
        print(f"Sample {i}: {row}")

    for candidate in ("TIME_PERIOD", "TIME_PERIOD_LABEL", "OBS_VALUE", "REF_AREA"):
        if candidate in fields:
            values = sorted({row.get(candidate, "") for row in rows if row.get(candidate, "")})
            print(f"{candidate}: {', '.join(values[:12])}" + (" ..." if len(values) > 12 else ""))

    print("\nInspection complete. Treat the returned columns and period values as authoritative;")
    print("do not assume the requested period was applied correctly without checking TIME_PERIOD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
