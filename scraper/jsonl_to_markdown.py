#!/usr/bin/env python3
"""
Convert article JSONL files to markdown for pasting into LLM chat UIs (e.g. ChatGPT, Gemini).
Reads one or more JSONL files and writes markdown with one clearly separated block per article.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List


def escape_md_heading(line: str) -> str:
    """Escape leading # so a line is not interpreted as a markdown heading."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return " " + line
    return line


def article_to_markdown(record: dict) -> str:
    """Convert one JSONL record to a markdown block. Handles null/empty fields."""
    title = record.get("title") or "Untitled"
    authors = record.get("authors")
    if not authors:
        authors_str = "N/A"
    else:
        authors_str = ", ".join(str(a) for a in authors)

    parts = [f"## {title}", ""]
    parts.append(f"**Authors:** {authors_str}  ")
    year = record.get("year")
    parts.append(f"**Year:** {year if year is not None else 'N/A'}  ")
    parts.append(f"**Journal:** {record.get('journal') or 'N/A'}  ")
    doi = record.get("doi")
    if doi:
        parts.append(f"**DOI:** {doi}  ")
    url = record.get("url")
    if url:
        parts.append(f"**URL:** {url}  ")
    vol = record.get("volume")
    issue = record.get("issue")
    if vol or issue:
        parts.append(f"**Volume/Issue:** {vol or '—'} / {issue or '—'}  ")
    parts.append("")

    abstract = record.get("abstract")
    if abstract and abstract.strip():
        # Escape leading # on any line so it doesn't become a heading
        abstract_escaped = "\n".join(escape_md_heading(ln) for ln in abstract.splitlines())
        parts.append("**Abstract:**  ")
        parts.append(abstract_escaped)
        parts.append("")

    parts.append("---")
    return "\n".join(parts)


# Department phrase at end of abstract in Management Science (IS department only)
MANAGEMENT_SCIENCE_IS_PHRASE = ", information systems"


def is_management_science_is_article(record: dict) -> bool:
    """True if this record is a Management Science article in the information systems department.
    The department is noted at the end of the abstract (e.g. '... accepted by X, information systems.').
    """
    abstract = record.get("abstract")
    if not abstract or not isinstance(abstract, str):
        return False
    return MANAGEMENT_SCIENCE_IS_PHRASE.lower() in abstract.lower()


def convert_file(jsonl_path: Path, filter_management_science_is: bool = False) -> List[dict]:
    """Read a JSONL file and return list of records.
    If filter_management_science_is is True, keep only records whose abstract contains ', information systems'.
    """
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if filter_management_science_is and not is_management_science_is_article(rec):
                    continue
                records.append(rec)
            except json.JSONDecodeError as e:
                print(f"  Warning: skip line {i} in {jsonl_path}: {e}", file=sys.stderr)
    return records


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_out = script_dir / "out_md"
    default_input_glob = script_dir / "out" / "*.jsonl"

    parser = argparse.ArgumentParser(
        description="Convert article JSONL files to markdown for LLM chat UIs."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="JSONL file(s) to convert; if not given, use scraper/out/*.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=default_out,
        help="Output directory for markdown files",
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        help="Write one file (all_articles.md) with all articles from all inputs",
    )
    args = parser.parse_args()

    if args.inputs:
        input_paths = [p.resolve() for p in args.inputs]
    else:
        input_paths = sorted(Path(p).resolve() for p in default_input_glob.parent.glob(default_input_glob.name))
    if not input_paths:
        print("No JSONL files found. Pass paths or run from repo with scraper/out/*.jsonl.", file=sys.stderr)
        sys.exit(1)

    args.out_dir = args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    def filter_ms_is(path: Path) -> bool:
        """Apply Management Science IS filter when input is the Management Science journal file."""
        return path.stem.startswith("management_science")

    if args.combined:
        combined_parts = ["# IS Journal Articles (Markdown for LLM UI)", ""]
        total = 0
        for path in input_paths:
            if not path.exists():
                print(f"Warning: skip missing {path}", file=sys.stderr)
                continue
            records = convert_file(path, filter_management_science_is=filter_ms_is(path))
            combined_parts.append(f"## Source: {path.stem}")
            combined_parts.append("")
            for rec in records:
                combined_parts.append(article_to_markdown(rec))
                combined_parts.append("")
                total += 1
        out_path = args.out_dir / "all_articles.md"
        out_path.write_text("\n".join(combined_parts), encoding="utf-8")
        print(f"Wrote {total} articles to {out_path}")
        return

    for path in input_paths:
        if not path.exists():
            print(f"Warning: skip missing {path}", file=sys.stderr)
            continue
        records = convert_file(path, filter_management_science_is=filter_ms_is(path))
        out_path = args.out_dir / f"{path.stem}.md"
        parts = [f"# {path.stem}", ""]
        for rec in records:
            parts.append(article_to_markdown(rec))
            parts.append("")
        out_path.write_text("\n".join(parts), encoding="utf-8")
        print(f"Wrote {len(records)} articles to {out_path}")


if __name__ == "__main__":
    main()
