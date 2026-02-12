#!/usr/bin/env python3
"""
Download recent articles from top IS journals via OpenAlex API.
Writes one JSONL file per journal (flat, LLM-friendly schema).
"""
import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import List, Optional

import requests

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
PER_PAGE = 200
DELAY_SECONDS = 1

# (display_name, filename_slug, OpenAlex source id from primary_location.source.id)
JOURNALS = [
    ("Information Systems Research", "information_systems_research", "S202812398"),
    ("MIS Quarterly", "mis_quarterly", "S57293258"),
    ("Management Science", "management_science", "S33323087"),
    ("Journal of Management Information Systems", "journal_of_management_information_systems", "S9954729"),
]


def slugify(s: str) -> str:
    """Lowercase, replace non-alphanumeric with underscore."""
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def build_abstract_from_inverted_index(inverted: dict) -> Optional[str]:
    """Reconstruct plaintext abstract from OpenAlex abstract_inverted_index."""
    if not inverted or not isinstance(inverted, dict):
        return None
    pairs = []
    for word, positions in inverted.items():
        for pos in positions:
            pairs.append((pos, word))
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pairs)


def work_to_record(work: dict, journal_name: str) -> dict:
    """Map OpenAlex work to flat LLM-friendly record."""
    authors = []
    for a in work.get("authorships") or []:
        author = a.get("author")
        if author and author.get("display_name"):
            authors.append(author["display_name"])

    abstract = None
    if work.get("abstract_inverted_index"):
        abstract = build_abstract_from_inverted_index(work["abstract_inverted_index"])

    year = work.get("publication_year")
    if year is not None:
        year = int(year)

    doi = None
    if work.get("ids") and work["ids"].get("doi"):
        doi = work["ids"]["doi"].replace("https://doi.org/", "")

    url = work.get("doi") or work.get("id")
    if url and isinstance(url, str) and not url.startswith("http"):
        url = f"https://doi.org/{url}" if doi else url

    primary = work.get("primary_location") or {}
    if not url and primary.get("landing_page_url"):
        url = primary["landing_page_url"]
    if not url and doi:
        url = f"https://doi.org/{doi}"

    biblio = work.get("biblio") or {}
    volume = biblio.get("volume")
    if volume is not None:
        volume = str(volume)
    issue = biblio.get("issue")
    if issue is not None:
        issue = str(issue)

    return {
        "title": work.get("title") or "",
        "authors": authors,
        "abstract": abstract,
        "year": year,
        "doi": doi,
        "journal": journal_name,
        "url": url,
        "volume": volume,
        "issue": issue,
    }


def fetch_works_for_source(
    source_id: str,
    from_date: str,
    to_date: str,
    session: requests.Session,
) -> List[dict]:
    """Paginate through OpenAlex works for a source and date range. Returns list of works."""
    # OpenAlex filter: primary_location.source.id matches the journal
    params = {
        "filter": f"primary_location.source.id:{source_id},from_publication_date:{from_date},to_publication_date:{to_date}",
        "per-page": PER_PAGE,
        "cursor": "*",
    }
    all_works = []
    cursor = "*"
    page = 0
    while True:
        page += 1
        params["cursor"] = cursor
        try:
            r = session.get(OPENALEX_WORKS_URL, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"  Request error (page {page}): {e}", file=sys.stderr)
            break
        except json.JSONDecodeError as e:
            print(f"  JSON error (page {page}): {e}", file=sys.stderr)
            break

        results = data.get("results") or []
        meta = data.get("meta") or {}
        next_cursor = meta.get("next_cursor")
        all_works.extend(results)
        if not next_cursor or len(results) < PER_PAGE:
            break
        cursor = next_cursor
        time.sleep(DELAY_SECONDS)
    return all_works


def main() -> None:
    parser = argparse.ArgumentParser(description="Download IS journal articles from OpenAlex to JSONL.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "out",
        help="Output directory for JSONL files",
    )
    parser.add_argument(
        "--from-date",
        default="2018-01-01",
        help="Start of publication date range (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to-date",
        default=date.today().isoformat(),
        help="End of publication date range (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    from_date = args.from_date
    to_date = args.to_date
    year_from = from_date[:4]
    year_to = to_date[:4]
    file_suffix = f"{year_from}_{year_to}.jsonl"

    session = requests.Session()
    session.headers.setdefault("User-Agent", "econis26-scraper/1.0 (mailto:optional@example.org)")

    for display_name, slug, source_id in JOURNALS:
        out_path = out_dir / f"{slug}_{file_suffix}"
        print(f"Fetching {display_name} -> {out_path.name} ...", flush=True)
        try:
            works = fetch_works_for_source(source_id, from_date, to_date, session)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue
        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for w in works:
                record = work_to_record(w, display_name)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        print(f"  Wrote {count} articles to {out_path}")
        time.sleep(DELAY_SECONDS)

    print("Done.")


if __name__ == "__main__":
    main()
