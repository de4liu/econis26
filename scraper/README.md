# IS Journal Articles Scraper

Downloads the last 8 years of articles from four top Information Systems journals via the [OpenAlex](https://openalex.org/) API and writes one **JSONL** file per journal. The output schema is flat and LLM-friendly (title, authors, abstract, year, DOI, journal, url, volume, issue).

## Journals

- Information Systems Research
- MIS Quarterly
- Management Science
- Journal of Management Information Systems

## Requirements

- Python 3.8+
- `requests` (see `requirements.txt`)

No API key required for OpenAlex.

## Usage

From the repo root or from `scraper/`:

```bash
pip install -r scraper/requirements.txt
python scraper/download_is_articles.py
```

Output files are written to `scraper/out/` by default, one file per journal, e.g.:

- `information_systems_research_2018_2026.jsonl`
- `mis_quarterly_2018_2026.jsonl`
- `management_science_2018_2026.jsonl`
- `journal_of_management_information_systems_2018_2026.jsonl`

### Optional arguments

- `--out-dir DIR` — Output directory (default: `scraper/out/` when run from repo root, or `out/` relative to the script).
- `--from-date YYYY-MM-DD` — Start of publication date range (default: `2018-01-01`).
- `--to-date YYYY-MM-DD` — End of publication date range (default: today).

Example:

```bash
python scraper/download_is_articles.py --out-dir ./data --from-date 2020-01-01 --to-date 2025-12-31
```

## Output format (JSONL)

Each line is one JSON object with the following fields:

| Field     | Type           | Description |
|----------|----------------|-------------|
| `title`  | string         | Article title |
| `authors`| array of strings | Author names |
| `abstract` | string or null | Plaintext abstract when available from OpenAlex |
| `year`   | int or null    | Publication year |
| `doi`    | string or null | DOI without URL prefix |
| `journal`| string         | Journal display name |
| `url`    | string or null | Landing page or DOI URL |
| `volume` | string or null | Volume |
| `issue`  | string or null | Issue |

Encoding is UTF-8. One JSON object per line; no pretty-printing.

## Convert JSONL to Markdown

To get markdown you can paste or attach in LLM chat UIs (e.g. ChatGPT, Gemini), convert the JSONL files with:

```bash
python scraper/jsonl_to_markdown.py
```

This reads all `scraper/out/*.jsonl` files and writes one markdown file per JSONL into `scraper/out_md/` (e.g. `information_systems_research_2018_2026.md`). Each article is a block with title, authors, year, journal, DOI, and abstract, separated by `---`.

### Optional arguments

- `inputs` — One or more JSONL paths; if omitted, uses `scraper/out/*.jsonl`.
- `--out-dir DIR` — Output directory for markdown (default: `scraper/out_md/`).
- `--combined` — Write a single file `all_articles.md` with all articles from all inputs.

Examples:

```bash
python scraper/jsonl_to_markdown.py
python scraper/jsonl_to_markdown.py --combined
python scraper/jsonl_to_markdown.py scraper/out/isr.jsonl --out-dir ./md
```

## Notes

- **Abstracts:** Not all works in OpenAlex have an open abstract (depends on publisher deposits). When missing, `abstract` is `null`.
- **Rate limiting:** The script waits 1 second between API requests to avoid throttling.
- **Idempotence:** Each run overwrites the JSONL files for the selected date range and output directory.
