import csv
import os
import re
from pathlib import Path

MANIFEST_PATH = Path('data/manifest.csv')
NOTES_DIR = Path('notes')
MANIFEST_HEADERS = ['paper_id', 'title', 'year', 'one_drive_path', 'share_link']


def infer_paper_id(filename: str):
    name = Path(filename).stem
    match = re.match(r'(?P<year>\d{4})[-_](?P<slug>.+)', name)
    if match:
        year = match.group('year')
        slug = re.sub(r'[^a-z0-9]+', '-', match.group('slug').lower()).strip('-')
        return f"{year}-{slug}", year
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return f"unknown-{slug}", ''


def load_manifest():
    entries = {}
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries[row['paper_id']] = row
    return entries


def append_manifest(row):
    file_exists = MANIFEST_PATH.exists()
    with MANIFEST_PATH.open('a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def note_path(paper_id: str) -> Path:
    return NOTES_DIR / f"{paper_id}.md"


def create_note(paper_id: str, year: str, path: str):
    p = note_path(paper_id)
    if p.exists():
        return
    yaml = [
        "---",
        f"paper_id: {paper_id}",
        "title: \"\"",
        "authors: []",
        "venue: ",
        f"year: {year}",
        "doi: ",
        "pdf_link: ",
        f"local_hint: {path}",
        "tags: []",
        "pestle: []",
        "methods: []",
        "code: ",
        "datasets: []",
        "my_rating: ",
        "replication_risk: ",
        "---",
        "## TL;DR（3行）",
        "- ",
        "- ",
        "- ",
        "",
        "## Contribution",
        "## Method",
        "## Results / Limits",
        "## For my work",
        "## Quotes",
        "## BibTeX",
        "```bibtex",
        "@inproceedings{",
        "}",
        "```",
    ]
    p.write_text("\n".join(yaml), encoding='utf-8')


def main():
    root = os.getenv('ONEDRIVE_PAPERS_ROOT')
    if not root or not os.path.isdir(root):
        raise SystemExit('ONEDRIVE_PAPERS_ROOT is not set or invalid')
    entries = load_manifest()
    for pdf in Path(root).rglob('*.pdf'):
        rel_path = os.path.relpath(pdf, root).replace('\\', '/')
        paper_id, year = infer_paper_id(pdf.name)
        if paper_id in entries:
            continue
        append_manifest({
            'paper_id': paper_id,
            'title': '',
            'year': year,
            'one_drive_path': rel_path,
            'share_link': ''
        })
        create_note(paper_id, year, rel_path)
        print(f'Added {paper_id}')


if __name__ == '__main__':
    main()
