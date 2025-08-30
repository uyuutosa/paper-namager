import os
from pathlib import Path
from typing import List

import streamlit as st

from paper_notes.review import (
    list_all_tags_and_years,
    find_notes,
    load_note_info,
    generate_review,
    try_extract_abstract_from_pdf,
    extract_pdf_metadata,
    update_note_front_matter,
)
from scripts.paper_sync import infer_paper_id, create_note, load_manifest, append_manifest  # type: ignore


st.set_page_config(page_title="Paper Review Builder", layout="wide")
st.title("📚 Review Builder")
st.caption("Select notes by tags/year/papers and generate a review markdown.")


@st.cache_data
def get_tags_years():
    return list_all_tags_and_years()


@st.cache_data
def list_note_options(tags: List[str], year: int | None):
    paths = find_notes(tags, year, [])
    items = [load_note_info(p) for p in paths]
    options = []
    for it in items:
        m = it['meta']  # type: ignore
        pid = str(m.get('paper_id', ''))
        title = str(m.get('title', '')) or pid
        year_str = str(m.get('year', ''))
        venue = str(m.get('venue', ''))
        label = f"{title} ({venue} {year_str}) [{pid}]"
        options.append((label, pid))
    return options


tags_all, years_all = get_tags_years()

with st.sidebar:
    st.header("Filters")
    sel_tags = st.multiselect("Tags", options=tags_all)
    sel_year = st.selectbox("Year", options=[None] + years_all, format_func=lambda x: "Any" if x is None else str(x))
    refresh = st.button("Refresh list")

note_options = list_note_options(sel_tags, sel_year)
if refresh:
    st.cache_data.clear()
    note_options = list_note_options(sel_tags, sel_year)

st.subheader("Select Papers")
selected = st.multiselect("Papers", options=[opt[0] for opt in note_options], default=[opt[0] for opt in note_options])
selected_pids = [pid for label, pid in note_options if label in selected]

st.subheader("Output Settings")
col1, col2 = st.columns(2)
with col1:
    title = st.text_input("Review Title", value="Literature Review")
    include_abstract = st.checkbox("Include Abstract (auto-extract from local PDFs)")
with col2:
    slug_parts: List[str] = []
    if sel_tags:
        slug_parts.append('-'.join(sorted(set([t.lower() for t in sel_tags]))))
    if sel_year:
        slug_parts.append(str(sel_year))
    if not slug_parts:
        slug_parts.append('custom')
    default_out = Path('reviews') / f"review-{'-'.join(slug_parts)}.md"
    out_path = Path(st.text_input("Output Path", value=str(default_out)))

st.markdown("---")

# --- PDF Uploads (Optional) ---
st.subheader("Upload PDFs (optional)")
st.caption("Attach PDFs to selected papers to auto-extract abstracts even without local files.")

if 'uploaded_pdfs' not in st.session_state:
    st.session_state.uploaded_pdfs = {}

uploads_root = Path('data') / 'uploads'
uploads_root.mkdir(parents=True, exist_ok=True)

if selected_pids:
    with st.expander("Manage uploads for selected papers", expanded=False):
        for label, pid in [(l, p) for (l, p) in note_options if p in selected_pids]:
            colu1, colu2 = st.columns([3, 2])
            with colu1:
                st.write(label)
            with colu2:
                uf = st.file_uploader(
                    f"Upload PDF for [{pid}]",
                    type=["pdf"],
                    key=f"upload_{pid}",
                    accept_multiple_files=False,
                    label_visibility='collapsed'
                )
                if uf is not None:
                    # Save to a stable path per pid
                    save_path = uploads_root / f"{pid}.pdf"
                    try:
                        with open(save_path, 'wb') as f:
                            f.write(uf.read())
                        st.session_state.uploaded_pdfs[pid] = save_path
                        st.success(f"Saved upload for {pid}")
                    except Exception as e:
                        st.error(f"Failed to save {pid}: {e}")
            # If we already have an uploaded file, show a short abstract preview
            existing = st.session_state.uploaded_pdfs.get(pid)
            if existing and existing.exists():
                try:
                    snippet = try_extract_abstract_from_pdf(existing)
                    if snippet:
                        st.caption(f"Abstract preview: {snippet[:200]}{'…' if len(snippet) > 200 else ''}")
                    else:
                        st.caption("No abstract text detected in first pages.")
                except Exception:
                    st.caption("Could not read uploaded PDF.")

    cols = st.columns(2)
    with cols[0]:
        if st.button("Clear all uploads"):
            st.session_state.uploaded_pdfs = {}
            st.rerun()

st.markdown("---")

generate = st.button("Generate Review", type="primary")

if generate:
    # Build mapping for uploaded PDFs only for selected papers
    uploaded_map = {pid: Path(p) for pid, p in (st.session_state.uploaded_pdfs or {}).items() if pid in selected_pids}
    content, items = generate_review(title, sel_tags, sel_year, selected_pids, include_abstract, uploaded_pdfs=uploaded_map)
    if not items:
        st.warning("No matching notes found. Adjust filters or selections.")
    else:
        # Preview and save
        st.success(f"Generated {len(items)} items")
        with st.expander("Preview Markdown", expanded=True):
            st.code(content, language="markdown")
        # Save to file
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding='utf-8')
            st.info(f"Saved to {out_path}")
        except Exception as e:
            st.error(f"Failed to save: {e}")
        st.download_button("Download Markdown", data=content, file_name=out_path.name, mime="text/markdown")

st.markdown("---")
st.caption("Tip: Ensure ONEDRIVE_PAPERS_ROOT is set for local PDF abstract extraction.")
st.markdown("---")

# --- Add New Paper (Upload) ---
st.subheader("Add New Paper (Upload)")
st.caption("Upload a new paper PDF to create a note and register it.")

new_pdfs = st.file_uploader(
    "Upload PDF(s)", type=["pdf"], accept_multiple_files=True, key="new_pdfs_uploader"
)

if new_pdfs:
    created = []
    uploads_root = Path('data') / 'uploads'
    uploads_root.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    for uf in new_pdfs:
        try:
            pid, year = infer_paper_id(uf.name)
            # Avoid conflicts
            note_file = Path('notes') / f"{pid}.md"
            if pid in manifest or note_file.exists():
                st.warning(f"Skip: {uf.name} → {pid} already exists")
                continue
            dest = uploads_root / f"{pid}.pdf"
            with open(dest, 'wb') as f:
                f.write(uf.read())
            # Register to manifest
            append_manifest({
                'paper_id': pid,
                'title': '',
                'year': year,
                'one_drive_path': str(dest),
                'share_link': ''
            })
            # Create initial note with local_hint pointing to the saved file
            create_note(pid, year, str(dest))
            created.append((pid, dest))
        except Exception as e:
            st.error(f"Failed to add {uf.name}: {e}")
    if created:
        # Extract metadata and update note/manifest for each created
        updated = []
        for pid, dest in created:
            md = extract_pdf_metadata(dest)
            # Update note front matter with extracted fields
            note_file = Path('notes') / f"{pid}.md"
            try:
                updates = {}
                if md.get('title'): updates['title'] = md['title']
                if md.get('authors'): updates['authors'] = md['authors']
                if md.get('year'): updates['year'] = md['year']
                if md.get('doi'): updates['doi'] = md['doi']
                if dest: updates['local_hint'] = str(dest)
                update_note_front_matter(note_file, updates)
                updated.append(pid)
            except Exception as e:
                st.warning(f"Note update failed for {pid}: {e}")
        st.success(f"Added {len(created)} paper(s): {', '.join(pid for pid,_ in created)}")
        # Clear caches so new notes appear in selection
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# --- Prompt Studio (Experimental) ---
st.subheader("Prompt Studio (Experimental)")
st.caption("Notebook LM風: 複数ノート/アップロードPDFを参照してプロンプトを実行（簡易合成）。")

if 'doc_weights' not in st.session_state:
    st.session_state.doc_weights = {}

prompt = st.text_area("Prompt", value="Compare the contributions and limitations of the selected papers.", height=120)

if selected_pids:
    with st.expander("Selected documents & weights", expanded=False):
        for label, pid in [(l, p) for (l, p) in note_options if p in selected_pids]:
            w = st.slider(f"{label}", min_value=0.0, max_value=2.0, value=float(st.session_state.doc_weights.get(pid, 1.0)), step=0.1)
            st.session_state.doc_weights[pid] = w

run_prompt = st.button("Run Prompt")

if run_prompt:
    # Prepare simple contexts (note body + optional abstract)
    docs = []
    for p in find_notes(sel_tags, sel_year, selected_pids):
        info = load_note_info(p)
        m = info['meta']  # type: ignore
        pid = str(m.get('paper_id',''))
        abstract = ''
        local_pdf = None
        try:
            local_pdf = (Path('data')/ 'uploads' / f"{pid}.pdf")
            if local_pdf.exists():
                abstract = try_extract_abstract_from_pdf(local_pdf)
        except Exception:
            abstract = ''
        weight = float(st.session_state.doc_weights.get(pid, 1.0))
        text = (abstract + "\n\n" + info['body']) if abstract else info['body']  # type: ignore
        docs.append((pid, text, weight))

    # Naive synthesis: include top-k by weight, clip length
    docs = sorted(docs, key=lambda x: x[2], reverse=True)
    k = min(5, len(docs))
    context_parts = []
    for pid, text, w in docs[:k]:
        snippet = text[:2000]
        context_parts.append(f"# [{pid}] (w={w})\n{snippet}")
    context = "\n\n---\n\n".join(context_parts)
    output = f"## Prompt\n{prompt}\n\n## Context (top {k})\n{context}\n\n## Output (placeholder)\nWrite your reasoning here or connect an LLM."
    with st.expander("Prompt Result", expanded=True):
        st.markdown(output)

st.markdown("---")
