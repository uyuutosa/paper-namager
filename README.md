# Paper Notes Repository

This repository stores structured notes for academic papers. PDF files live in OneDrive, while this repo tracks metadata and Markdown notes.

- `data/manifest.csv` maps `paper_id` to PDF locations.
- `notes/` holds one Markdown file per paper with YAML front matter.
- `scripts/paper_sync.py` scans the OneDrive directory and creates missing manifest entries and note templates.
- GitHub Actions build a searchable MkDocs site from the notes.

See `KB_README.md` for terminology and tagging guidelines.
