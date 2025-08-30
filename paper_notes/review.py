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
        if val.startswith('[') and val.endswith(']'):
            try:
                data[key] = ast.literal_eval(val)
            except Exception:
                data[key] = [v.strip() for v in val.strip('[]').split(',') if v.strip()]
        elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            data[key] = val[1:-1]
        else:
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
    pattern = re.compile(rf"^\s*{re.escape(heading)}\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return ''
    start = m.end()
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
    m = re.search(r"```[a-zA-Z]*\n(.*?)\n```", sec, re.DOTALL)
    return m.group(1).strip() if m else ''


def try_extract_abstract_from_pdf(pdf_path: Path, max_pages: int = 2) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ''


def extract_pdf_metadata(pdf_path: Path) -> Dict[str, object]:
    """Best-effort PDF metadata extraction.

    Returns keys: title(str), authors(List[str]), year(str), doi(str), keywords(List[str])
    Missing fields are empty strings or empty lists.
    """
    meta: Dict[str, object] = {
        'title': '',
        'authors': [],
        'year': '',
        'doi': '',
        'keywords': [],
    }
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return meta
    try:
        reader = PdfReader(str(pdf_path))
        info = reader.metadata or {}
        title = getattr(info, 'title', '') or info.get('/Title', '') if isinstance(info, dict) else str(getattr(info, 'title', '') or '')
        author = getattr(info, 'author', '') or info.get('/Author', '') if isinstance(info, dict) else str(getattr(info, 'author', '') or '')
        subj = getattr(info, 'subject', '') or info.get('/Subject', '') if isinstance(info, dict) else ''
        keywords = getattr(info, 'keywords', '') or info.get('/Keywords', '') if isinstance(info, dict) else ''
        create_date = getattr(info, 'creation_date', '') or info.get('/CreationDate', '') if isinstance(info, dict) else ''
        if title:
            meta['title'] = str(title).strip()
        if author:
            # split by common separators
            auths = [a.strip() for a in str(author).replace(';', ',').split(',') if a.strip()]
            if auths:
                meta['authors'] = auths
        if keywords:
            kws = [k.strip() for k in str(keywords).replace(';', ',').split(',') if k.strip()]
            if kws:
                meta['keywords'] = kws
        # crude year from creation date
        import re as _re
        m = _re.search(r'(19|20)\d{2}', str(create_date))
        if m:
            meta['year'] = m.group(0)

        # scan first page for DOI and potentially better title line
        text = ''
        try:
            text = reader.pages[0].extract_text() or ''
        except Exception:
            text = ''
        # DOI
        mdoi = _re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', text, flags=_re.IGNORECASE)
        if mdoi:
            meta['doi'] = mdoi.group(1)
        # If title empty, take the first non-empty line (heuristic)
        if not meta['title']:
            for line in text.splitlines():
                s = line.strip()
                if len(s) > 8 and len(s.split()) >= 3:
                    meta['title'] = s
                    break
    except Exception:
        pass
    return meta
    try:
        reader = PdfReader(str(pdf_path))
        text = ''
        for i in range(min(max_pages, len(reader.pages))):
            try:
                text += reader.pages[i].extract_text() or ''
            except Exception:
                continue
        text = re.sub(r'\s+', ' ', text)
        m = re.search(r'(abstract[:\.]?\s*)(.{100,800})', text, re.IGNORECASE)
        if m:
            return m.group(2).strip()
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
    if not hint:
        return None
    # 1) Absolute path or workspace-relative path
    p = Path(hint)
    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p
    # 2) Under ONEDRIVE_PAPERS_ROOT if provided
    root = os.getenv('ONEDRIVE_PAPERS_ROOT')
    if root:
        candidate = Path(root) / hint
        if candidate.exists():
            return candidate
    # 3) Fallback to default uploads directory
    uploads = Path('data') / 'uploads'
    candidate2 = uploads / Path(hint).name
    if candidate2.exists():
        return candidate2
    return None


def update_note_front_matter(path: Path, updates: Dict[str, object]) -> None:
    """Update YAML-like front matter of a note with provided keys.

    Only touches the front matter block; preserves the body.
    """
    text = read_file(path)
    meta, offset = parse_front_matter(text)
    # merge
    for k, v in updates.items():
        meta[k] = v
    # render simple YAML lines (keep a stable key order)
    def fmt_val(v: object) -> str:
        if isinstance(v, list):
            return '[' + ', '.join([f'"{str(x)}"' if (',' in str(x) or ' ' in str(x)) else str(x) for x in v]) + ']'
        if isinstance(v, str):
            # quote if contains colon
            if ':' in v or v.strip() == '' or v.strip() != v:
                return f'"{v}"'
            return v
        return str(v)
    keys_order = [
        'paper_id','title','authors','venue','year','doi','pdf_link','local_hint',
        'tags','pestle','methods','code','datasets','my_rating','replication_risk'
    ]
    lines: List[str] = ['---']
    for k in keys_order:
        if k in meta:
            lines.append(f"{k}: {fmt_val(meta[k])}")
    # include any extra keys
    for k, v in meta.items():
        if k not in keys_order:
            lines.append(f"{k}: {fmt_val(v)}")
    lines.append('---')
    body = text[offset:]
    new_text = '\n'.join(lines) + '\n' + body.lstrip('\n')
    path.write_text(new_text, encoding='utf-8')


def build_review_markdown(title: str, items: List[Dict[str, object]], include_abstract: bool) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("> Generated by paper_notes.review")
    lines.append("")
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
        tldr: List[str] = it.get('tldr') or []  # type: ignore
        if tldr:
            lines.append("**TL;DR:**")
            for b in tldr:
                lines.append(f"- {b}")
            lines.append("")
        if include_abstract:
            abs_text = it.get('abstract') or ''  # type: ignore
            if abs_text:
                lines.append("**Abstract (auto-extracted):**")
                lines.append(abs_text)
                lines.append("")
        pdf_link = str(m.get('pdf_link', ''))
        local_pdf = resolve_local_pdf(m)
        link_parts = [f"Note: [{pid}]({it['path']})"]  # type: ignore
        if pdf_link:
            link_parts.append(f"PDF: {pdf_link}")
        if local_pdf:
            link_parts.append(f"Local: {local_pdf}")
        lines.append(' · '.join(link_parts))
        lines.append("")

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


def list_all_tags_and_years() -> Tuple[List[str], List[int]]:
    tags_set = set()
    years_set = set()
    for p in NOTES_DIR.glob('*.md'):
        meta, _ = parse_front_matter(read_file(p))
        for t in meta.get('tags') or []:
            tags_set.add(str(t))
        y = meta.get('year')
        try:
            y_int = int(y)
            if y_int:
                years_set.add(y_int)
        except Exception:
            pass
    return sorted(tags_set), sorted(years_set)


def generate_review(title: str, filter_tags: List[str], year: Optional[int],
                    papers: List[str], include_abstract: bool,
                    uploaded_pdfs: Optional[Dict[str, Path]] = None) -> Tuple[str, List[Dict[str, object]]]:
    notes = find_notes(filter_tags, year, papers)
    if not notes:
        return '', []
    items = [load_note_info(p) for p in notes]
    if include_abstract:
        for it in items:
            m = it['meta']  # type: ignore
            pid = str(m.get('paper_id', ''))
            abs_text = ''
            # Prefer uploaded file bound to this paper id, fallback to local resolution
            if uploaded_pdfs and pid in uploaded_pdfs:
                abs_text = try_extract_abstract_from_pdf(uploaded_pdfs[pid])
            else:
                local_pdf = resolve_local_pdf(m)
                if local_pdf:
                    abs_text = try_extract_abstract_from_pdf(local_pdf)
            it['abstract'] = abs_text
    content = build_review_markdown(title, items, include_abstract=include_abstract)
    return content, items
