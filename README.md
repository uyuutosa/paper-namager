# Paper Notes Repository（論文ナレッジベース）

学術論文のPDFはOneDriveに保存し、本リポジトリではメタデータとMarkdownノートをバージョン管理します。ノートはMkDocs(Material)で検索可能な静的サイトとして公開できます。

このREADMEでは、セットアップから論文の追加・タグ運用・サイト生成/デプロイまでを具体的に説明します。

**構成概要**
- `data/manifest.csv`: `paper_id` とPDFの場所、共有リンクなどのメタデータを管理
- `notes/`: 各論文1ファイルのMarkdownノート（YAMLフロントマター付き）
- `scripts/paper_sync.py`: OneDrive配下をスキャンし、未登録のPDFからmanifestとノートを自動生成
- `scripts/generate_review.py`: 複数のノート/PDFからレビューペーパーを自動生成
- `site/mkdocs.yml`: サイト設定（Material for MkDocs）
- `tags/`: タグ別インデックス（手動で管理）
- `KB_README.md`: 用語・タグの運用ガイド
 - `reviews/`: 生成されたレビューMarkdownの置き場


**前提条件**
- Dev Container 利用時: ビルド時に `mkdocs-material` 等のセットアップは自動で完了します（`.devcontainer/Dockerfile`）。
- Dev Container を使わない場合のみ:
  - Python 3.x と `pip install mkdocs-material`
- OneDriveに論文PDFのルートフォルダがあること（環境変数 `ONEDRIVE_PAPERS_ROOT` で指す）

なお、依存関係の管理には高速な `uv` を用います（リビルド不要で `uv sync` により最新化）。


**ディレクトリ構成（抜粋）**
- `data/manifest.csv`: 論文カタログ
- `data/vocab.yaml`: タグ・軸（pestle/methods）の語彙集
- `notes/<paper_id>.md`: ノート本体
- `scripts/paper_sync.py`: 同期スクリプト
- `site/mkdocs.yml`: サイト設定
- `tags/*.md`: タグ別インデックス


**paper_id とファイル命名規則**
- PDFファイル名が `YYYY-<slug>.pdf` または `YYYY_<slug>.pdf` 形式なら、`paper_id` は `YYYY-slug` として推定されます。
- それ以外は `unknown-<slug>` となります。
- 詳細は `scripts/paper_sync.py` の `infer_paper_id` を参照。


**manifest.csv のカラム**
- `paper_id`: ノート/参照のキー（例: `2025-smith-multiagent-x`）
- `title`: 論文タイトル
- `year`: 出版年
- `one_drive_path`: OneDrive内のPDF相対パス
- `share_link`: 共有用リンク（任意、後から追記可）


**ノートのYAMLフロントマター（例）**
`notes/2025-smith-multiagent-x.md` を参照。テンプレートは同期スクリプトが自動生成します（必要に応じて追記/編集）。
- `paper_id, title, authors, venue, year, doi, pdf_link, local_hint`
- `tags, pestle, methods, code, datasets`
- `my_rating, replication_risk`
- セクション例: TL;DR, Contribution, Method, Results/Limits, For my work, Quotes, BibTeX


**タグ運用**
- 一貫性のため、`data/vocab.yaml` の語彙から選択して付与してください。
- タグ別ページを作る場合は `tags/<tag>.md` を作成し、対象ノートへのリンクを列挙します。
- サイトのナビゲーションにタグページを載せるには `site/mkdocs.yml` の `nav` に追記します。


## 使い方

**1) 最初のセットアップ**
- Dev Container を開く（VS Code: "Reopen in Container"）。必要なツールはコンテナビルド時に導入済みです。
- OneDrive の論文PDFルートをホスト側で環境変数に設定（絶対パスで。`~` は使わない）
  - macOS/Linux（一時設定）: `export ONEDRIVE_PAPERS_ROOT="/absolute/path/to/OneDrive/Papers"`
  - Windows PowerShell（一時設定）: `$env:ONEDRIVE_PAPERS_ROOT = "C:\\absolute\\path\\to\\OneDrive\\Papers"`
- ホストの OneDrive をコンテナにマウントする場合は、`.devcontainer/devcontainer.local.json` を作成して `.devcontainer/devcontainer.local.json.example` を参考に `mounts` を有効にしてください。
  - マウント先は `/workspaces/onedrive`（スクリプトはこのパスを前提に動作）。
  - よくあるつまずき: `~` は展開されないため必ず絶対パスを指定してください。

依存関係（uv）:
- 本リポジトリは `pyproject.toml` で依存を管理します。
- コンテナ初回作成時に `postCreate` で `uv` を自動インストールし `uv sync` を実行します。
- 以降、依存の更新はコンテナ内で `uv sync` を叩くだけで反映されます（再ビルド不要）。
- 仮想環境は `.venv/` に作成され、VS Code は自動でそのPythonを使用します。


**2) 論文PDFの追加 → manifest とノート自動生成**
- macOS/Linux（Bash等）
  - `ONEDRIVE_PAPERS_ROOT=/path/to/OneDrive/Papers python scripts/paper_sync.py`
- Windows（PowerShell）
  - `.\u200bscripts\add_paper.ps1 -PdfPath "C:\\path\\to\\OneDrive\\Papers\\somepaper.pdf"`
  - 指定したPDFの親ディレクトリをルートとして `paper_sync.py` を実行します。

スクリプトの挙動：
- OneDrive配下の `*.pdf` を再帰的に走査
- 既存の `data/manifest.csv` を読み込み、未登録のPDFだけを追加
- `data/manifest.csv` に行を追記し、対応する `notes/<paper_id>.md` をテンプレートから生成
- 既に同名ノートがある場合はスキップ

エラー対処：
- `ONEDRIVE_PAPERS_ROOT is not set or invalid` → 環境変数の設定とパスの存在を確認


**3) ノート編集とタグ付け**
- `notes/<paper_id>.md` を開き、YAMLと本文を追記
- `tags` や `methods` は `data/vocab.yaml` の語彙に合わせる
- 共通の用語・評価軸・タグの背景は `KB_README.md` を参照


**4) サイトのプレビュー（コンテナ内）**
- 起動: `mkdocs serve --config-file site/mkdocs.yml`
- ブラウザで `http://127.0.0.1:8000` を開く

設定のポイント（`site/mkdocs.yml`）
- `docs_dir: ..`（リポジトリルートをドキュメントソースとして扱います）
- `nav` に Home（`README.md`）、Notes、Tags を定義


**5) デプロイ（GitHub Pages）**
- 既に GitHub Actions ワークフロー（`.github/workflows/site.yml`）が用意されています。
- `main` ブランチへpushすると自動でビルド・デプロイされます。
- Pages の公開設定はリポジトリの Settings → Pages で有効化してください。

ワークフローの要点：
- `mkdocs-material` をインストールし、`mkdocs build --config-file site/mkdocs.yml` を実行
- 生成物はリポジトリ外の `_site` ディレクトリへ出力し、Pages アーティファクトとしてアップロード/公開

## レビューペーパー自動生成（複数PDF/ノートを集約）

深いサーベイ結果から、対象論文群をまとめたレビューMarkdownを生成できます。

概要:
- 入力の選択: `--tag`、`--year`、`--paper <paper_id>` で対象ノートをフィルタ
- 出力: `reviews/review-<slug>.md`（デフォルト）
- 付加情報: ノートの TL;DR 箇条書き、BibTeX を統合
- オプション: `--abstract` でPDF先頭からAbstractを自動抽出（`pypdf` が必要）

前提（Abstract抽出を使う場合のみ）:
- `uv add pypdf` もしくは `uv sync`（`pyproject.toml` に同梱済み）
- OneDriveのPDFをコンテナにマウントし、`ONEDRIVE_PAPERS_ROOT` を設定（ノートの `local_hint` を解決）

例:
- タグで絞り込み（multi-agent を2025年で絞る）
  - `python scripts/generate_review.py --tag multi-agent --year 2025 --title "Multi-Agent Review 2025"`
- 複数タグ/任意の年、Abstractも試す
  - `python scripts/generate_review.py --tag safety --tag debate --abstract --title "Safety & Debate Review"`
- 特定の `paper_id` 群を指定
  - `python scripts/generate_review.py --paper 2025-smith-multiagent-x --paper 2024-wang-xyz`

出力の見た目:
- Overview表（タイトル/年/会議/タグ/ノートへのリンク）
- 論文ごとの小見出し、TL;DR（ノートから）、Abstract（任意、自動抽出）
- BibTeXをReferencesとしてまとめて末尾に出力

MkDocs ナビゲーションへの追加（任意）:
- `site/mkdocs.yml` の `nav` に `reviews/README.md` や生成されたファイルを項目として追加してください。

## 簡易UI（Streamlit）
- 起動: `uv run streamlit run ui/app.py`
- 機能: タグ/年で絞り込み、対象ノートを選択、タイトルとAbstract有無を指定してレビューMarkdownを生成・保存・ダウンロード
- Abstract抽出を使う際は `ONEDRIVE_PAPERS_ROOT` を設定してローカルPDFを解決できるようにしてください。

## 依存管理（uv）チートシート
- 依存を同期: `uv sync`
- パッケージ追加: `uv add <package>`（例: `uv add pypdf`）
- パッケージ削除: `uv remove <package>`
- Pythonバージョン固定: `uv python pin 3.11`
- 仮想環境を使った実行: `uv run mkdocs serve --config-file site/mkdocs.yml`


## ベストプラクティス
- PDFファイル名は `YYYY-title-or-keywords.pdf` 形式にする（`paper_id` が安定）
- 追加後なるべく早く `title/authors/venue/year/doi/pdf_link` を埋める
- `share_link` は共有権限に注意して付与
- タグとメソッドは `data/vocab.yaml` の語彙に沿って厳密に運用
- サイトの `nav` に新規ノートやタグページを適宜追加


## 参考ファイル
- リポジトリ概要: `README.md`
- 用語・タグ運用: `KB_README.md`
- 同期スクリプト: `scripts/paper_sync.py`
- サイト設定: `site/mkdocs.yml`
- GitHub Actions: `.github/workflows/site.yml`


## ライセンス
本リポジトリは MIT License です（`LICENSE` を参照）。
