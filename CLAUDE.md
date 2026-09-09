# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 現状

このリポジトリは現時点で空である（ソースコード・設定ファイルなし、Git 未初期化）。
Python による自動化スクリプト群を格納する目的で作成された。実装が追加されたら、
本ファイルにビルド/テスト/実行コマンドとアーキテクチャの説明を追記すること。

## Git 運用ルール

- **コードを変更するたびに、コミットして GitHub にプッシュする。** 変更を作業ツリーに
  残したまま次のタスクに進まない。
- まだ Git リポジトリではないため、最初のコード変更時に `git init` し、GitHub 上に
  リモートリポジトリを作成して `git remote add origin <url>` で接続してから push する。
- 1 つの論理的変更につき 1 コミット。コミットメッセージは変更内容が分かる形で記述する。
- `main` ブランチへ直接コミットして push してよい（個人の自動化プロジェクトのため）。

## セットアップ（実装追加後に更新）

Python プロジェクトの標準的な初期化例:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # または pyproject.toml / uv
```

- 依存管理・テストランナー・Lint ツールを導入したら、その実コマンドをここに記載する
  （例: `pytest`、単体テスト実行 `pytest path/to/test_file.py::test_name`、
  `ruff check .`、`ruff format .`）。
