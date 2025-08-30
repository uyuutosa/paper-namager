# 仕様書（現状まとめ）

## 概要
- 目的: 論文PDFとノート（Markdown）を管理し、複数ノートからレビューMarkdownを生成する。
- 運用: PDFはローカル（OneDrive クライアントで同期済みフォルダ、またはアプリへの直接アップロード）。ノートとメタデータはGitで管理。
- UI: Streamlitで簡易UIを提供（フィルタ・選択・アップロード・生成）。
- CLI: スクリプトでレビュー生成／OneDrive配下のPDFをスキャンして登録。

## 機能一覧
- ノート管理
  - `notes/<paper_id>.md` にYAMLフロントマター＋本文を保存。
  - `data/manifest.csv` で論文の基本メタデータを管理。
- PDF取り込み
  - 「新規アップロード」: UIからPDFをアップロードし、`paper_id` 推定→ `manifest` 追記→ ノート自動生成。
  - 「既存ノートへの添付」: UIで選択中の論文に対しPDFをアップロードし、アブストラクト抽出に利用。
  - OneDrive運用: `ONEDRIVE_PAPERS_ROOT` とノートの `local_hint` でローカルPDFを解決。
- レビュー生成
  - UI: タグ・年・論文選択、タイトル、Abstract有無を指定してMarkdownを生成・保存・ダウンロード。
  - CLI: `scripts/generate_review.py` で同等の生成を実行可能。
- サイト生成
  - MkDocs(Material)でドキュメントサイトをプレビュー／デプロイ可能（`site/mkdocs.yml`）。

## ディレクトリ構成（抜粋）
- `data/manifest.csv` — 論文の目録（paper_id, year など）
- `data/uploads/` — UIでアップロードしたPDFの保存先（`<paper_id>.pdf`）
- `notes/` — 各論文のノート（Markdown）
- `scripts/` — CLIスクリプト群
  - `generate_review.py` — レビュー生成
  - `paper_sync.py` — OneDrive配下PDFをスキャンして `manifest` 追記＆ノート生成
- `paper_notes/review.py` — コア処理（抽出・生成・探索）
- `ui/app.py` — Streamlit UI
- `site/mkdocs.yml` — サイト設定（docs_dirはリポジトリルート）

## データモデル
- manifest.csv カラム
  - `paper_id` — ノート/参照のキー（例: `2025-smith-xyz`）
  - `title` — タイトル（空でも可）
  - `year` — 出版年（空可）
  - `one_drive_path` — PDFへのパス（OneDrive相対 または ローカル保存の絶対/相対パス）
  - `share_link` — 共有リンク（任意）
- ノート（YAMLフロントマター）
  - 主要フィールド: `paper_id, title, authors, venue, year, doi, pdf_link, local_hint`
  - タグ類: `tags, pestle, methods`
  - その他: `code, datasets, my_rating, replication_risk`
  - 本文セクション例: `## TL;DR（3行）`, `## Contribution`, `## Method`, `## Results / Limits`, `## For my work`, `## Quotes`, `## BibTeX`

## UI仕様（Streamlit `ui/app.py`）
- 画面構成
  - Sidebar: `Tags`, `Year`, `Refresh list`
  - Main:
    - `Select Papers` — ノート候補をラベル表示し複数選択
    - `Output Settings` — タイトル、Abstract抽出の有無、保存先パス
    - `Upload PDFs (optional)` — 選択中の各論文にPDFを添付して抽出に利用（プレビュー表示あり）
    - `Add New Paper (Upload)` — 新規PDFをアップロードし、`paper_id` 推定→ `manifest` 追記→ ノート生成
    - `Generate Review` — レビューMarkdownを生成・表示・保存・ダウンロード
- 新規アップロード時の挙動
  - `infer_paper_id` で `paper_id` と `year` をファイル名から推定
  - 重複（同一 `paper_id`）はスキップ
  - PDFは `data/uploads/<paper_id>.pdf` に保存
  - `manifest.csv` に追記、`notes/<paper_id>.md` をテンプレで作成
  - 生成後は `st.rerun()` で一覧を更新
- Abstract抽出の優先順
  1. UIで紐づけたアップロードPDF（`data/uploads/<paper_id>.pdf`）
  2. ノートの `local_hint` が指すパス（絶対/相対）
  3. `ONEDRIVE_PAPERS_ROOT/local_hint`
  4. フォールバック: `data/uploads/<local_hintのファイル名>`

## CLI仕様
- `scripts/generate_review.py`
  - 引数: `--title`, `--tag (repeatable)`, `--year`, `--paper (repeatable)`, `--output`, `--abstract`
  - 出力: `reviews/review-<slug>.md`（デフォルト）。`--abstract` 指定時、上記のPDF解決ロジックで抽出。
- `scripts/paper_sync.py`
  - 前提: `ONEDRIVE_PAPERS_ROOT` が指すディレクトリ配下にPDFがあること
  - 処理: `*.pdf` を再帰走査→ 未登録だけ `manifest.csv` に追記→ 対応ノートをテンプレ生成
  - `paper_id` 推定ルール: `YYYY-<slug>` または `YYYY_<slug>` を優先。なければ `unknown-<slug>`

## OneDrive連携
- ログイン/API連携は不要。ホストで同期済みのOneDriveフォルダをコンテナにマウントして参照。
- 環境変数: `ONEDRIVE_PAPERS_ROOT`
  - Devcontainerでは `/.devcontainer/devcontainer.json` の `remoteEnv` で既定 `/workspaces/onedrive` を設定
  - 実マウントは `/.devcontainer/devcontainer.local.json` の `mounts` でホストのパスを指定（例ファイルあり）

## 依存・実行環境
- Python 3.11
- 依存（`pyproject.toml` 管理, `uv sync`）
  - UI: `streamlit`
  - 抽出: `pypdf`
  - サイト: `mkdocs`, `mkdocs-material`
- 起動例
  - UI: `uv run streamlit run ui/app.py`
  - CLI: `python scripts/generate_review.py --tag multi-agent --year 2025 --abstract`
  - サイト: `uv run mkdocs serve --config-file site/mkdocs.yml`

## エラーと対処
- `ONEDRIVE_PAPERS_ROOT is not set or invalid`
  - OneDrive運用時の環境変数未設定。絶対パスで設定し、マウントを確認。
- Abstract抽出が空になる
  - PDF先頭1〜2ページにAbstract記載が無い／抽出に失敗。アップロードPDFを添付して試行。
- `st.experimental_rerun` が無い
  - Streamlit 1.49以降は `st.rerun()` を使用（UIは修正済み）。

## 今後の拡張（案）
- メタデータ入力UI（タイトル・著者・DOI等）を新規アップロード時に追加
- `paper_id` 手動上書き（重複時のリネームサポート）
- DeepResearch結果（JSON/Markdown）のアップロードとノートへの自動マージ
- 既存ノート本文への抽出結果の自動追記（見出し選択対応）

---
最終更新: この仕様はリポジトリの現状コード（`ui/app.py`, `paper_notes/review.py`, `scripts/*.py`）に基づく要約です。

## 追加仕様（拡張計画）

本節は、今後実装する機能の仕様を合意するためのドラフトです。優先度順に段階実装を想定します。

### PDFの情報抽出（メタデータ）
- 目的: PDFから自動でメタデータ（タイトル、著者、発行年、DOI、キーワード等）を抽出し、ノートYAMLやmanifestへ反映する。
- 抽出対象とソース:
  - 埋め込みメタ: XMP/Info（`pypdf`）から `Title`, `Author`, `CreationDate`, `Subject`, `Keywords` を取得。
  - 本文ヘッダ: 1–2ページをOCRなしでテキスト抽出し、正規表現でタイトル・著者行・DOIを推定。
  - DOIリゾルバ（任意）: DOI検出時にCrossref等のAPIで書誌情報を補完（ネットワーク可否で分岐）。
- 反映先と優先順位:
  1. ユーザー手入力
  2. DOIリゾルバ
  3. PDF埋め込みメタ
  4. 本文推定
- UI/操作:
  - 新規アップロード時に「メタデータ自動抽出」を走らせ、プレビュー編集ダイアログでYAMLへ確定保存。
  - 既存ノートにも「再抽出」ボタンを提供。
- 失敗時の扱い: 抽出できないフィールドは空のままとし、警告をUIに表示。

### Notebook LM風マルチドキュメント指定インターフェース
- 目的: 複数のノート/アップロードPDF/外部Markdownを同時に参照しながら要約・比較・レビュー生成を行う。
- UI要件:
  - ドキュメント選択パネル: 検索＋チェックボックスで複数選択、ドラッグで優先度（重み）変更。
  - ドキュメントごとの設定: 役割タグ（背景/中核/反証など）、重み、最大トークン、除外セクション。
  - プレビューパネル: 選択ドキュメントの抜粋とメタデータを確認。
- 処理仕様（LangChain想定）:
  - ローダ: ノート（Markdown）、PDF、任意テキストを読み込み。
  - 分割: セマンティック/固定長チャンク（例: 800–1200字、重なり20%）。
  - 埋め込み: `text-embedding-3-large` 互換 or ローカル埋め込みを選択可能。
  - ベクタストア: Chroma/FAISS。コレクションを `paper_id` で分離。
  - 取得: クエリ＋重み付きフィルタでk件取得、重複抑制（MMR）。
  - 合成: RAG（Retriever → Reranker[任意] → LLM）で最終回答。

### プロンプト入力領域
- 目的: 任意の指示（System/Instruction/Examples）を編集し、プリセット管理できるようにする。
- UI:
  - タブ切替: System / Instructions / Examples / Output Style。
  - テンプレ管理: 保存・読込、バージョン差分表示。
  - トークン見積り: 現在の選択ドキュメントとプロンプトの合計トークンを表示。
- 変数プレースホルダ: `{title}`, `{year}`, `{tags}`, `{selected_docs}` などをテンプレに埋め込み。

### LangChainによるAI処理
- コンポーネント:
  - Loaders: Markdown, PDF, 任意テキスト
  - Splitter: RecursiveCharacterTextSplitter（日本語最適設定）
  - Embeddings: OpenAI/AzureOpenAI/ローカル（切替）
  - Vector Store: Chroma/FAISS
  - Retriever: 重み付き検索、MMR、Rerank（bge-reranker 等、任意）
  - LLM: OpenAI/Azure/Local（ストリーム出力対応）
  - Chains: QA/RAG、比較表生成、レビューMarkdown生成
- 設定:
  - `.env` or `settings.toml` でプロバイダ鍵・モデル名・閾値・k値を管理。
  - 実行ログは`data/runs/`に保存（プロンプト・選択文書・出力）。

### アーキテクチャ（MVC＋レイヤード）
- レイヤ:
  - Presentation(UI): React/Streamlit（暫定）
  - Application: ユースケース（コマンド/クエリ）、入出力DTO
  - Domain: エンティティ（Paper, Note, Review, DocumentChunk）とドメインサービス
  - Infrastructure: ストレージ（FS/VectorDB）、外部API（Crossref/LLM）、リポジトリ
- 依存方向: UI → Application → Domain → Infrastructure（Domainは外部に依存しない）
- 移行方針: 現在のStreamlitはプロトタイプUIとし、API化（FastAPI）後にReactへ移行。

### フロントエンド（React）
- 技術選定: Next.js + TypeScript + UIライブラリ（Chakra UI or MUI） + TanStack Query。
- 主要画面:
  - Documents: 検索/選択/アップロード
  - Prompt Studio: プロンプト編集・プリセット管理
  - Runs: 実行履歴、比較、再実行
  - Review Builder: 生成・編集・エクスポート
- Backend: FastAPIでAPI提供（/documents, /prompts, /runs, /rag など）。

### VS Code Launch（全自動起動）
- 目的: ワンクリックで開発環境一式（フロント/バック/DB）を起動。
- 例（将来の構成; 参考JSON）:
  - Compound: `App: All-in-One`
    - `Backend (FastAPI)`: `uv run fastapi dev backend/main.py`（ポート8001）
    - `Frontend (React)`: `npm run dev`（ポート3000）
    - `Vector DB (Chroma)`: `uv run python scripts/start_chroma.py`
- 現状は以下を利用可能:
  - `Review UI (Streamlit)`（既存）
  - `Generate Review (CLI)`（既存）
  - `MkDocs: Serve`（既存）
