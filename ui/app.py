import os
from pathlib import Path
from typing import List

import streamlit as st

from paper_notes.review import (
    list_all_tags_and_years,
    find_notes,
    load_note_info,
    generate_review,
)


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

generate = st.button("Generate Review", type="primary")

if generate:
    content, items = generate_review(title, sel_tags, sel_year, selected_pids, include_abstract)
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

