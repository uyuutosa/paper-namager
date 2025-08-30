import argparse
import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Optional, Tuple


NOTES_DIR = Path('notes')
REVIEWS_DIR = Path('reviews')


def read_file(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='ignore')


def parse_front_matter(text: str) -> Tuple[Dict[str, object], int]:
    """
    Parse simple YAML front-matter delimited by --- at top of a note file.
    Returns (data, end_index_of_front_matter_in_chars).
    Supports scalar strings/numbers and list literals like [a, b].
    """
    if not text.startswith('---'):
        return {}, 0
    end = text.find('\n---', 3)
    if end == -1:
        return {}, 0
    header = text[3:end].strip('\n')
    data: Dict[str, object] = {}
    for line in header.splitlines():
        if not line.strip() or line.strip().startswith('#'):
            continue
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key = key.strip()
        val = val.strip()
        # Try to coerce lists and quoted strings
        if val.startswith('[') and val.endswith(']'):
            try:
                data[key] = ast.literal_eval(val)
            except Exception:
                data[key] = [v.strip() for v in val.strip('[]').split(',') if v.strip()]
        elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            data[key] = val[1:-1]
        else:
            # Try int, float, bool; fallback to string (can be empty)
            low = val.lower()
            if low in {'true', 'false'}:
                data[key] = (low == 'true')
            else:
                try:
                    data[key] = int(val)
                except ValueError:
                    try:
                        data[key] = float(val)
                    except ValueError:
                        data[key] = val
    return data, end + len('\n---')


def extract_section(text: str, heading: str) -> str:
    """Extract markdown section by its exact heading (e.g., '## TL;DR（3行）')."""
    # Find heading line
    pattern = re.compile(rf"^\s*{re.escape(heading)}\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return ''
    start = m.end()
    # Next H2 or H1
    next_heading = re.search(r"^\s*##\s+|^\s*#\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip('\n')


def parse_tldr_bullets(section_text: str) -> List[str]:
    out = []
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith('- '):
            out.append(line[2:].strip())
    return out


def extract_bibtex(text: str) -> str:
    sec = extract_section(text, '## BibTeX')
    if not sec:
        return ''
    # Extract fenced code block contents
    m = re.search(r"```[a-zA-Z]*\n(.*?)\n```", sec, re.DOTALL)
    return m.group(1).strip() if m else ''


def try_extract_abstract_from_pdf(pdf_path: Path, max_pages: int = 2) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ''
    try:
        reader = PdfReader(str(pdf_path))
        text = ''
        for i in range(min(max_pages, len(reader.pages))):
            try:
                text += reader.pages[i].extract_text() or ''
            except Exception:
                continue
        text = re.sub(r'\s+', ' ', text)
        # Look for Abstract section heuristically
        m = re.search(r'(abstract[:\.]?\s*)(.{100,800})', text, re.IGNORECASE)
        if m:
            return m.group(2).strip()
        # Fallback: first 500 chars
        return text[:500].strip()
    except Exception:
        return ''


def find_notes(filter_tags: List[str], year: Optional[int], papers: List[str]) -> List[Path]:
    candidates = []
    for p in sorted(NOTES_DIR.glob('*.md')):
        text = read_file(p)
        meta, _ = parse_front_matter(text)
        pid = str(meta.get('paper_id', ''))
        if papers and pid not in papers:
            continue
        if year and int(meta.get('year', 0) or 0) != year:
            continue
        if filter_tags:
            tags = [str(t).lower() for t in (meta.get('tags') or [])]
            if not set([t.lower() for t in filter_tags]) & set(tags):
                continue
        candidates.append(p)
    return candidates


def load_note_info(p: Path) -> Dict[str, object]:
    text = read_file(p)
    meta, _ = parse_front_matter(text)
    tldr = parse_tldr_bullets(extract_section(text, '## TL;DR（3行）'))
    bib = extract_bibtex(text)
    return {
        'path': str(p),
        'meta': meta,
        'tldr': tldr,
        'bibtex': bib,
        'body': text,
    }


def resolve_local_pdf(meta: Dict[str, object]) -> Optional[Path]:
    hint = str(meta.get('local_hint') or '').strip()
    root = os.getenv('ONEDRIVE_PAPERS_ROOT')
    if not hint or not root:
        return None
    candidate = Path(root) / hint
    return candidate if candidate.exists() else None


def build_review_markdown(title: str, items: List[Dict[str, object]], include_abstract: bool) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("> Generated by scripts/generate_review.py")
    lines.append("")
    # Overview table
    lines.append("## Overview")
    lines.append("| Paper | Year | Venue | Tags | Notes |")
    lines.append("|---|---:|---|---|---|")
    for it in items:
        m = it['meta']  # type: ignore
        pid = str(m.get('paper_id', ''))
        title = str(m.get('title', '')) or pid
        year = str(m.get('year', ''))
        venue = str(m.get('venue', ''))
        tags = ', '.join([str(t) for t in (m.get('tags') or [])])
        note_link = f"[{pid}]({it['path']})"  # type: ignore
        lines.append(f"| {title} | {year} | {venue} | {tags} | {note_link} |")
    lines.append("")

    # Per-paper summaries
    for idx, it in enumerate(items, 1):
        m = it['meta']  # type: ignore
        pid = str(m.get('paper_id', ''))
        title = str(m.get('title', '')) or pid
        authors = ', '.join([str(a) for a in (m.get('authors') or [])])
        venue = str(m.get('venue', ''))
        year = str(m.get('year', ''))
        doi = str(m.get('doi', ''))
        lines.append(f"## {idx}. {title}")
        meta_line = f"{authors} · {venue} {year}"
        if doi:
            meta_line += f" · DOI: {doi}"
        lines.append(meta_line.strip(' ·'))
        lines.append("")
        # TL;DR
        tldr: List[str] = it.get('tldr') or []  # type: ignore
        if tldr:
            lines.append("**TL;DR:**")
            for b in tldr:
                lines.append(f"- {b}")
            lines.append("")
        # Abstract (optional)
        if include_abstract:
            abs_text = it.get('abstract') or ''  # type: ignore
            if abs_text:
                lines.append("**Abstract (auto-extracted):**")
                lines.append(abs_text)
                lines.append("")
        # Link to note and PDF
        pdf_link = str(m.get('pdf_link', ''))
        local_pdf = resolve_local_pdf(m)
        link_parts = [f"Note: [{pid}]({it['path']})"]  # type: ignore
        if pdf_link:
            link_parts.append(f"PDF: {pdf_link}")
        if local_pdf:
            link_parts.append(f"Local: {local_pdf}")
        lines.append(' · '.join(link_parts))
        lines.append("")

    # References (BibTeX if available)
    bibs = [str(it.get('bibtex')) for it in items if it.get('bibtex')]
    if bibs:
        lines.append("## References (BibTeX)")
        lines.append("```bibtex")
        for b in bibs:
            lines.append(b)
            if not b.endswith('\n'):
                lines.append('')
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description='Generate a review paper markdown from selected notes/PDFs.')
    ap.add_argument('--title', default='Literature Review', help='Title of the review markdown')
    ap.add_argument('--tag', dest='tags', action='append', default=[], help='Filter by tag (repeatable)')
    ap.add_argument('--year', type=int, help='Filter by exact year')
    ap.add_argument('--paper', dest='papers', action='append', default=[], help='Select specific paper_id (repeatable)')
    ap.add_argument('--output', '-o', help='Output path (default: reviews/<slug>.md)')
    ap.add_argument('--abstract', action='store_true', help='Try to auto-extract abstract from PDFs (needs pypdf)')
    args = ap.parse_args()

    if not NOTES_DIR.exists():
        raise SystemExit(f'Notes directory not found: {NOTES_DIR}')

    notes = find_notes(args.tags, args.year, args.papers)
    if not notes:
        raise SystemExit('No matching notes found')

    items = [load_note_info(p) for p in notes]
    if args.abstract:
        for it in items:
            m = it['meta']  # type: ignore
            local_pdf = resolve_local_pdf(m)
            abs_text = ''
            if local_pdf:
                abs_text = try_extract_abstract_from_pdf(local_pdf)
            if not abs_text and m.get('pdf_link'):
                # If share link exists but not locally mounted, we skip fetching due to offline policy
                abs_text = ''
            it['abstract'] = abs_text

    # Determine output path
    slug_parts = []
    if args.tags:
        slug_parts.append('-'.join(sorted(set([t.lower() for t in args.tags]))))
    if args.year:
        slug_parts.append(str(args.year))
    if not slug_parts:
        slug_parts.append('custom')
    slug = '-'.join(slug_parts)
    out_path = Path(args.output) if args.output else (REVIEWS_DIR / f"review-{slug}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    content = build_review_markdown(args.title, items, include_abstract=args.abstract)
    out_path.write_text(content, encoding='utf-8')
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()

