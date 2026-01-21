# CI/CD Pipeline Documentation

このドキュメントは、MOSプロジェクトのCI/CDパイプラインについて説明します。

---

## 概要

MOSプロジェクトでは、GitHub Actionsを使用したCI/CDパイプラインを構築しています。すべてのプッシュとプルリクエストに対して自動的にテスト、リント、フォーマットチェック、Dockerビルドが実行されます。

---

## ワークフロー

### 1. CI ワークフロー (`.github/workflows/ci.yml`)

**トリガー条件:**
- `main`, `develop`, `claude/**` ブランチへのプッシュ
- `main`, `develop` ブランチへのプルリクエスト

**ジョブ構成:**

#### Job 1: Lint (リントとフォーマットチェック)

コード品質をチェックします:
- **Black**: コードフォーマットチェック
- **Flake8**: リント（コーディング規約チェック）
- **MyPy**: 型チェック（エラーでも継続）

```bash
# ローカルで実行する場合
cd backend
make format-check  # Blackフォーマットチェック
make lint          # Flake8リント
make type-check    # MyPy型チェック
```

#### Job 2: Test (テスト実行)

PostgreSQLとRedisサービスを起動してテストを実行:
- PostgreSQL 16
- Redis 7
- pytest + pytest-asyncio
- カバレッジレポート生成

```bash
# ローカルで実行する場合
cd backend
make test          # テスト実行
make test-cov      # カバレッジレポート付きテスト
```

**環境:**
- Python 3.11
- PostgreSQL 16 (localhost:5432)
- Redis 7 (localhost:6379)

#### Job 3: Test Matrix (複数バージョンテスト)

Python 3.11と3.12でモデルテストを実行:
- SQLiteを使用した軽量テスト
- 互換性確認

---

### 2. Docker ワークフロー (`.github/workflows/docker.yml`)

**トリガー条件:**
- `main`, `develop`, `claude/**` ブランチへのプッシュ
- `main`, `develop` ブランチへのプルリクエスト

**ジョブ構成:**

#### Job: Docker Build Test

Dockerイメージとdocker-composeの動作確認:

1. **Docker イメージビルド**: 単一イメージのビルド確認
2. **docker-compose ビルド**: 全サービスのビルド確認
3. **サービス起動**: PostgreSQLとRedisを起動
4. **ヘルスチェック**: サービスが正常に動作することを確認
5. **マイグレーション実行**: データベース初期化
6. **API起動**: FastAPI起動とヘルスチェック

```bash
# ローカルで実行する場合
cd backend
make docker-build  # イメージビルド
make docker-up     # サービス起動
curl http://localhost:8000/health  # ヘルスチェック
make docker-down   # サービス停止
```

---

## 開発者向けガイド

### ローカルでCIチェックを実行

コミット前に、ローカルでCI と同じチェックを実行することを推奨します:

```bash
cd backend

# すべてのCIチェックを実行（推奨）
make ci

# または個別に実行
make format-check  # フォーマットチェック
make lint          # リント
make type-check    # 型チェック
make test          # テスト
```

### コード自動フォーマット

```bash
cd backend
make format  # Black でコードをフォーマット
```

### テスト実行

```bash
cd backend

# 基本的なテスト実行
make test

# カバレッジレポート付き
make test-cov

# 特定のテストのみ実行
pytest tests/models/ -v
pytest tests/integration/test_tasks.py -v
pytest tests/integration/test_tasks.py::test_create_task -v
```

---

## コード品質基準

### Black (フォーマッター)

- **行の長さ**: 最大100文字
- **ターゲットバージョン**: Python 3.11
- **設定ファイル**: `backend/pyproject.toml`

### Flake8 (リンター)

- **行の長さ**: 最大100文字
- **無視するエラー**: E203, W503
- **設定ファイル**: `backend/.flake8`

主な規約:
- インポートは標準ライブラリ → サードパーティ → ローカルの順
- 未使用のインポートは削除
- 関数は適切にドキュメント化

### MyPy (型チェッカー)

- **Pythonバージョン**: 3.11
- **設定ファイル**: `backend/pyproject.toml`
- **モード**: `ignore_missing_imports = true` (サードパーティライブラリの型チェックスキップ)

注意: 現在型チェックエラーはCIを失敗させません（`continue-on-error: true`）

---

## トラブルシューティング

### 問題: CIでテストが失敗する

**原因1: PostgreSQL固有の機能を使用している**
- SQLiteテストでは一部の機能（ON CONFLICT等）が動作しません
- PostgreSQLサービスが起動しているCIジョブで確認してください

**原因2: 環境変数が不足している**
- `.env`ファイルが正しく設定されているか確認
- `OPENAI_API_KEY`等の必須環境変数が設定されているか確認

**解決方法:**
```bash
# ローカルでPostgreSQLを使ってテスト
cd backend
docker-compose up -d db redis
make test
```

---

### 問題: Blackのフォーマットチェックが失敗する

**エラー:**
```
error: would reformat app/some_file.py
```

**解決方法:**
```bash
cd backend
make format  # 自動フォーマット
git add .
git commit -m "Format code with Black"
```

---

### 問題: Flake8のリントエラー

**よくあるエラー:**
- `F401`: インポートしているが使用していない
- `E501`: 行が長すぎる（100文字超）
- `F841`: 変数が使用されていない

**解決方法:**
```bash
cd backend
make lint  # エラーを確認

# エラーを修正
# - 未使用のインポートを削除
# - 長い行を分割
# - 未使用の変数を削除または _ を使用
```

---

### 問題: Dockerビルドが失敗する

**原因: requirements.txtの依存関係エラー**

**解決方法:**
```bash
cd backend

# ローカルでビルドテスト
docker build -t mos-backend:test .

# エラーログを確認
docker-compose build
docker-compose logs
```

---

## CI/CDパイプラインの拡張

### 新しいチェックの追加

`.github/workflows/ci.yml` にステップを追加:

```yaml
- name: Run Security Check
  run: |
    cd backend
    pip install bandit
    bandit -r app/ -ll
```

### カバレッジ閾値の設定

`backend/pyproject.toml` にカバレッジ設定を追加:

```toml
[tool.coverage.report]
fail_under = 80  # 80%未満でCIを失敗させる
```

### デプロイメントの追加

メインブランチへのマージ時に自動デプロイ:

```yaml
deploy:
  name: Deploy to Production
  runs-on: ubuntu-latest
  needs: [lint, test, docker-build]
  if: github.ref == 'refs/heads/main'
  steps:
    - name: Deploy to server
      run: |
        # デプロイスクリプトを実行
```

---

## ベストプラクティス

### コミット前

1. ローカルでCIチェックを実行: `make ci`
2. テストを追加/更新
3. ドキュメントを更新

### プルリクエスト前

1. すべてのCIチェックがパスすることを確認
2. カバレッジが下がっていないか確認
3. コードレビューの準備

### マージ前

1. CI/CDパイプラインがすべて成功していることを確認
2. コードレビューが承認されていることを確認
3. コンフリクトがないことを確認

---

## GitHub Actions の使用状況

### ワークフロー実行時間の目安

- **Lint**: 約1-2分
- **Test**: 約3-5分
- **Docker Build**: 約5-8分
- **合計**: 約10-15分

### GitHub Actions の制限

- **無料枠**: 月2,000分（パブリックリポジトリは無制限）
- **同時実行**: 最大20ジョブ（Freeプラン）

最適化のヒント:
- キャッシュを活用（pip cache, Docker layer cache）
- 不要なジョブは `if` 条件で制限
- テストを並列化

---

## 参考リンク

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)

---

## 次のステップ

CI/CDパイプラインをさらに強化する場合:

1. **セキュリティスキャン**: Bandit, Safety
2. **依存関係チェック**: Dependabot
3. **パフォーマンステスト**: Locust, k6
4. **自動デプロイ**: Heroku, AWS, GCP
5. **通知**: Slack, Discord連携

詳細はプロジェクトの要件に応じて追加してください。
