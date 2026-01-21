# Management Ourselves System (MOS)

![CI](https://github.com/yourusername/MOS-Management-Ourselves-Systems/workflows/CI/badge.svg)
![Docker Build](https://github.com/yourusername/MOS-Management-Ourselves-Systems/workflows/Docker%20Build/badge.svg)

MOS（Management Ourselves System）は、個人のタスクを **チャットから抽出 → 提案（Draft）→ ユーザーが確定** する形で管理し、朝/昼/夕のフォローで「見落とし」と「停滞」を減らすためのAIタスク管理システムです。

本リポジトリのPhase1（MVP）は **1人利用・Web・ローカル運用優先** を前提に、最短で価値が出る「タスク化・階層管理・定期フォロー」を作ります。

---

## 目的
- タスクの発生源（頭の中・チャット）をそのまま受け取り、構造化して管理できるようにする
- **親タスク/子タスク**（階層）で分解し、実行単位を小さくする
- **朝/昼/夕** の軽いフォローで、期限・停滞・優先度を継続的にリマインドする

---

## コンセプト / 非目標（Phase1）
### コンセプト
- **提案（Draft）→ 確定（Task）** を必ず挟み、LLMの誤りでDBの真実を汚さない
- 期限は **日付が主**（時刻は任意の補足情報）

### 非目標（Phase1ではやらない）
- 外部サービスへの自律実行（メール送信・予定作成など）
- カレンダー同期、外部通知（Discord/LINE/Slack等）
- 本格的な認証・マルチユーザー対応（将来対応余地は残す）

---

## 用語
- **Task（確定タスク）**：DB上の真実。状態/優先度/期限/親子関係を持つ
- **Draft（提案）**：LLMが生成したタスク案。ユーザーが accept/reject して確定する
- **Project**：タスクの集合（タグ的な束ね）。個人タスクを見やすくするための分類
- **Follow-up**：朝/昼/夕に生成されるフォロー要約（アプリ内メッセージ）

---

## Phase 1（MVP）機能
- チャット入力からタスク案（Draft）を生成
- Draftの **accept / reject**
- タスク管理（CRUD）
- **親タスク/子タスク**（階層、深さはまず 2〜3段推奨）
- プロジェクト管理（フラット）
- フォロー要約（**朝/昼/夕**・アプリ内）

---

## ロードマップ（概要）
- **Phase2**：通知・カレンダー同期（スパム抑制/要約が重要）
- **Phase3**：UI/UX強化（ガント/添付/テーマ/認証）
- **Phase4**：外部連携（OAuth、情報取得、低リスク操作からの準自律実行）
- **Phase5**：秘書化（先回りの提案、ユーザーの最終決定権は維持）
- **Phase6**：リリース（共同作業、権限設計、監査、攻撃耐性）
- **PhaseEX**：Virtual Doppelgänger（将来構想）

---

## アーキテクチャ（Phase1）
- Frontend：Web（Next.js想定）
- Backend：FastAPI
- DB：Postgres
- Queue/Worker：Redis + Celery
- LLM：`services/llm.py` に集約（プロバイダ差し替え可能）
- スケジュール：APScheduler（朝/昼/夕のフォロー生成）

---

## データ設計（要点）
- `tasks`：親子階層は `parent_task_id` で表現
- `projects`：フラットな分類
- `messages`：チャットログ
- `task_drafts`：LLM提案（Draft）を保持して accept/reject
- `agent_runs`：抽出ログ（デバッグ・再現性のため）
- `followup_runs`：朝/昼/夕の実行記録（重複抑制に利用）

期限の扱い：
- `due_date`（date）を主とし、`due_time`（time）は任意

---

## セキュリティ / プライバシー基本方針（Phase1）
- 収集データ最小化（必要なもののみ）
- 自律実行は行わず、基本は「提案→ユーザー確定」
- LLM出力はJSONスキーマ検証し、壊れた場合は保存/確定しない
- `agent_runs` により、抽出結果を再現・検証できるようにする

---

## セットアップ

### クイックスタート（Docker）

**推奨**: Docker Composeを使用した完全なセットアップ手順は **[Docker Setup Guide](./docs/DOCKER_SETUP.md)** を参照してください。

#### 必要なもの
- Docker & Docker Compose
- OpenAI API キー（または代替LLMバックエンド）

#### 基本手順
```bash
# 1. リポジトリをクローン
git clone https://github.com/yourusername/MOS-Management-Ourselves-Systems.git
cd MOS-Management-Ourselves-Systems/backend

# 2. 環境変数を設定
cp .env.example .env
# .env を編集して OPENAI_API_KEY などを設定

# 3. Docker Composeで起動
docker-compose up -d

# 4. APIが起動していることを確認
curl http://localhost:8000/health
```

**詳細なトラブルシューティング、本番環境設定、代替LLMバックエンドについては [Docker Setup Guide](./docs/DOCKER_SETUP.md) を参照。**

---

## ドキュメント

- **[Docker Setup Guide](./docs/DOCKER_SETUP.md)**: Docker環境でのセットアップ・運用ガイド
- **[LLM Providers](./docs/LLM_PROVIDERS.md)**: LLMバックエンドの選択と設定（OpenAI / Claude CLI / Ollama）
- **[CI/CD Pipeline](./docs/CI_CD.md)**: 継続的インテグレーション/デプロイメントガイド

---

## Secrets / 設定について
- APIキー、ID/PW等のシークレットは **ソースコードにハードコーディングしない**
- ローカル開発は `.env` を使用（`.env` は **Git管理しない**）
- 配布用に `.env.example` を用意し、実際の値は各自の環境で設定する
- 本番相当では Secret Manager / Docker Secrets / K8s Secrets 等から注入する

