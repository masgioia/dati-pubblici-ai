"""Download and analyse ISTAT resident-population data via SDMX CSV."""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

# ISTAT's legacy SDMX endpoint is a documented fallback for temporal-filter
# issues observed on the newer endpoint. See README for source documentation.
API_URL = "http://sdmx.istat.it/SDMXWS/rest/data/22_289/.TOTAL..9.99../"
SOURCE_URL = "https://esploradati.istat.it/SDMXWS/rest/data/IT1,22_289/A..JAN.9.TOTAL.99/"


def download_population(start_year: int, end_year: int, timeout: int = 90) -> pd.DataFrame:
    """Fetch the selected years as CSV and return raw observations."""
    if start_year > end_year:
        raise ValueError("start_year must be <= end_year")
    response = requests.get(
        API_URL,
        params={"startPeriod": start_year, "endPeriod": end_year},
        headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    if not response.text.strip():
        raise RuntimeError("ISTAT returned an empty response")
    df = pd.read_csv(io.StringIO(response.text), dtype=str)
    if df.empty:
        raise RuntimeError("ISTAT returned no observations for the selected period")
    df.columns = [c.strip().upper() for c in df.columns]
    if "OBS_VALUE" not in df.columns or "TIME_PERIOD" not in df.columns:
        raise RuntimeError("Unexpected ISTAT CSV schema. Columns received: " + ", ".join(df.columns))
    return df


def identify_area_column(df: pd.DataFrame) -> str:
    """Identify the territorial code column without assuming one API label."""
    for name in ("ITTER107", "REF_AREA", "TERRITORIO", "GEO"):
        if name in df.columns:
            return name
    possible = [c for c in df.columns if "TERR" in c or "AREA" in c or "ITTER" in c]
    if len(possible) == 1:
        return possible[0]
    raise RuntimeError("Cannot identify territory column. CSV columns: " + ", ".join(df.columns))


def regional_changes(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    """Calculate population changes by NUTS-2 region, requiring one value per year."""
    area_col = identify_area_column(df)
    data = df.copy()
    data["YEAR"] = pd.to_numeric(data["TIME_PERIOD"], errors="coerce")
    data["POPULATION"] = pd.to_numeric(data["OBS_VALUE"], errors="coerce")
    data = data[data["YEAR"].isin([start_year, end_year])].copy()
    if data.empty:
        raise RuntimeError(f"No observations found for {start_year} and {end_year}")

    # Italian NUTS-2 regional codes have the form ITC1, ITF3, ITH5, etc.
    codes = data[area_col].fillna("").astype(str).str.strip()
    data = data[codes.str.match(r"^IT[A-Z][0-9]$")].copy()
    if data.empty:
        raise RuntimeError(f"No NUTS-2 regional codes recognised in {area_col!r}; inspect raw CSV.")
    duplicated = data.duplicated(subset=[area_col, "YEAR"], keep=False)
    if duplicated.any():
        raise RuntimeError("Multiple observations per region/year: additional dimensions must be filtered.")
    pivot = data.pivot(index=area_col, columns="YEAR", values="POPULATION")
    if start_year not in pivot.columns or end_year not in pivot.columns:
        raise RuntimeError("The requested start/end years are not both present")
    pivot = pivot.dropna(subset=[start_year, end_year])
    result = pd.DataFrame({
        "codice_regione": pivot.index,
        f"popolazione_{start_year}": pivot[start_year].values,
        f"popolazione_{end_year}": pivot[end_year].values,
    })
    start_col, end_col = f"popolazione_{start_year}", f"popolazione_{end_year}"
    result["variazione_assoluta"] = result[end_col] - result[start_col]
    result["variazione_percentuale"] = result["variazione_assoluta"] / result[start_col] * 100
    return result.sort_values("variazione_percentuale", ascending=False).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2014)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data/regional_population_change.csv"))
    parser.add_argument("--raw-output", type=Path, default=Path("data/istat_population_raw.csv"))
    args = parser.parse_args()
    try:
        raw = download_population(args.start_year, args.end_year)
        changes = regional_changes(raw, args.start_year, args.end_year)
        args.raw_output.parent.mkdir(parents=True, exist_ok=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        raw.to_csv(args.raw_output, index=False)
        changes.to_csv(args.output, index=False)
        print(f"Fonte dati: {SOURCE_URL}")
        print(f"Osservazioni scaricate: {len(raw)} | Regioni confrontabili: {len(changes)}")
        print(changes.to_string(index=False, formatters={"variazione_percentuale": "{:.2f}%".format}))
        print(f"\nCSV grezzo: {args.raw_output}\nRisultati: {args.output}")
        return 0
    except (requests.RequestException, ValueError, RuntimeError, pd.errors.ParserError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
