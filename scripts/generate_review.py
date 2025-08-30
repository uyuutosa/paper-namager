import argparse
from pathlib import Path
from typing import List

from paper_notes.review import generate_review


def main():
    ap = argparse.ArgumentParser(description='Generate a review paper markdown from selected notes/PDFs.')
    ap.add_argument('--title', default='Literature Review', help='Title of the review markdown')
    ap.add_argument('--tag', dest='tags', action='append', default=[], help='Filter by tag (repeatable)')
    ap.add_argument('--year', type=int, help='Filter by exact year')
    ap.add_argument('--paper', dest='papers', action='append', default=[], help='Select specific paper_id (repeatable)')
    ap.add_argument('--output', '-o', help='Output path (default: reviews/<slug>.md)')
    ap.add_argument('--abstract', action='store_true', help='Try to auto-extract abstract from PDFs (needs pypdf)')
    args = ap.parse_args()

    content, items = generate_review(args.title, args.tags, args.year, args.papers, args.abstract)
    if not items:
        raise SystemExit('No matching notes found')

    slug_parts: List[str] = []
    if args.tags:
        slug_parts.append('-'.join(sorted(set([t.lower() for t in args.tags]))))
    if args.year:
        slug_parts.append(str(args.year))
    if not slug_parts:
        slug_parts.append('custom')
    slug = '-'.join(slug_parts)
    out_path = Path(args.output) if args.output else Path('reviews') / f"review-{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding='utf-8')
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
