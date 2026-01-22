# Task Actions System

タスクアクションシステムは、タスクに対して自動化されたアクションを提案・実行する機能です。

## 概要

### システムの特徴

1. **LLM駆動の提案**: タスク内容を分析し、適切なアクションを自動提案
2. **承認フロー**: 全てのアクションは実行前にユーザーの承認が必要
3. **安全性重視**: dry-runモード、ロールバック機能、詳細なロギング
4. **拡張可能**: 新しいアクションタイプを簡単に追加可能

### アクションライフサイクル

```
PROPOSED   →   APPROVED   →   EXECUTING   →   COMPLETED
(提案)         (承認済)        (実行中)         (完了)
   ↓              ↓
CANCELLED      CANCELLED                      FAILED
(キャンセル)    (キャンセル)                    (失敗)
```

## 利用可能なアクション

### 1. send_email - メール送信

タスクに関連するメールを送信します。

**パラメータ:**
```json
{
  "to": "recipient@example.com",
  "subject": "メール件名",
  "body": "メール本文",
  "cc": ["cc@example.com"],  // オプション
  "priority": "high"          // オプション: low/normal/high
}
```

**使用例:**
- クライアントへのミーティング招待
- プロジェクトメンバーへの進捗報告
- 納品物の送信通知

**注意事項:**
- SMTP設定が必要（.envファイルで設定）
- 送信後のメールは取り消せません

### 2. fetch_web_info - Web情報取得

指定されたURLから情報を取得してタスクに添付します。

**パラメータ:**
```json
{
  "url": "https://example.com/page",
  "extract_fields": ["title", "description", "content"]  // オプション
}
```

**使用例:**
- 競合サイトの価格調査
- 技術記事の内容確認
- イベント詳細の取得

**注意事項:**
- 公開されているページのみアクセス可能
- JavaScript実行が必要なページは取得できない場合あり

### 3. search_web - Web検索

キーワードでWeb検索を実行し、結果を取得します。

**パラメータ:**
```json
{
  "query": "検索キーワード",
  "num_results": 5  // デフォルト: 5
}
```

**使用例:**
- 市場調査
- 技術情報の収集
- 最新ニュースの確認

**注意事項:**
- 検索API設定が必要（Google Custom Search APIなど）

### 4. set_reminder - リマインダー設定

タスクのリマインダーを設定します。

**パラメータ:**
```json
{
  "remind_at": "1 hour"  // または "tomorrow 9am", "2024-12-25 10:00"
}
```

**サポートされる時間指定:**
- 相対時間: "1 hour", "30 minutes", "2 days"
- 日時: "tomorrow", "next Monday", "9am"
- 絶対時刻: "2024-12-25 10:00"

**使用例:**
- 期限前のリマインダー設定
- ミーティング前の通知
- フォローアップの予定

**注意事項:**
- ロールバック可能（設定後にキャンセル可能）

### 5. calculate - 計算実行

数式を評価するか、単位変換を実行します。

**パラメータ（計算）:**
```json
{
  "expression": "2 + 2 * 3"
}
```

**パラメータ（単位変換）:**
```json
{
  "convert_from": "100 USD",
  "convert_to": "JPY"
}
```

**サポートされる関数:**
- 基本: `abs`, `round`, `min`, `max`, `sum`
- 数学: `sqrt`, `pow`, `log`
- 三角関数: `sin`, `cos`, `tan`
- 定数: `pi`, `e`

**使用例:**
- 見積もり計算
- 為替換算
- 面積・体積の計算

**注意事項:**
- セキュリティのため、評価可能な式は制限されています
- 単位変換は将来実装予定（現在はプレースホルダー）

## API使用方法

### アクション提案取得

タスクに対してLLMがアクションを提案します。

```bash
POST /api/tasks/{task_id}/actions/propose
Content-Type: application/json

{
  "task_title": "クライアントXへの提案書作成",
  "task_description": "12月25日までに提案書を作成してメール送信",
  "task_metadata": {
    "priority": "high",
    "due_date": "2024-12-25"
  }
}
```

**レスポンス:**
```json
[
  {
    "action_type": "send_email",
    "parameters": {
      "to": "client-x@example.com",
      "subject": "提案書送付の件",
      "body": "..."
    },
    "reasoning": "タスクにメール送信が含まれているため",
    "confidence": 0.85
  },
  {
    "action_type": "set_reminder",
    "parameters": {
      "remind_at": "2024-12-23 09:00"
    },
    "reasoning": "期限2日前にリマインダーを設定",
    "confidence": 0.75
  }
]
```

### アクション作成

提案されたアクションをタスクに登録します（PROPOSED状態）。

```bash
POST /api/tasks/{task_id}/actions
Content-Type: application/json

{
  "action_type": "send_email",
  "parameters": {
    "to": "client@example.com",
    "subject": "件名",
    "body": "本文"
  },
  "reasoning": "メール送信が必要",
  "confidence": 0.8
}
```

### タスクのアクション一覧取得

```bash
GET /api/tasks/{task_id}/actions?status=proposed
```

### アクション承認

```bash
POST /api/actions/{action_id}/approve
```

### アクション実行

```bash
POST /api/actions/{action_id}/execute
Content-Type: application/json

{
  "dry_run": false
}
```

**dry_run=true の場合:**
- 実際の変更は行わず、シミュレーションのみ実行
- 事前にアクションの動作を確認できる

### アクションキャンセル

```bash
POST /api/actions/{action_id}/cancel
```

### アクションロールバック

```bash
POST /api/actions/{action_id}/rollback
```

**注意:** ロールバック可能なアクションのみ実行できます。

## 開発者向け：新しいアクションの追加

### 1. アクションタイプの定義

`backend/app/models/task_action.py` にアクションタイプを追加:

```python
class ActionType(str, enum.Enum):
    # 既存のアクション...
    MY_NEW_ACTION = "my_new_action"
```

### 2. アクション実行クラスの作成

`backend/app/services/actions/my_action.py` を作成:

```python
from app.services.actions.base import ActionExecutor, ActionResult
from app.services.actions.registry import action_registry

@action_registry.register("my_new_action")
class MyNewAction(ActionExecutor):
    """
    新しいアクションの説明

    Parameters:
        param1: パラメータ1の説明
        param2: パラメータ2の説明
    """

    def validate_parameters(self) -> None:
        """パラメータ検証"""
        required = ["param1", "param2"]
        for param in required:
            if param not in self.parameters:
                raise ValueError(f"Missing parameter: {param}")

    async def execute(self) -> ActionResult:
        """アクション実行"""
        try:
            # 実際の処理をここに記述
            result = do_something(self.parameters)

            return ActionResult(
                success=True,
                data={"result": result}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def dry_run(self) -> ActionResult:
        """ドライラン（シミュレーション）"""
        return ActionResult(
            success=True,
            data={
                "dry_run": True,
                "message": "Would execute: ..."
            }
        )

    def get_description(self) -> str:
        """アクションの説明を返す"""
        return f"Execute my new action with {self.parameters}"

    def get_safety_warnings(self) -> list[str]:
        """安全性に関する警告"""
        return [
            "This action will modify external resources",
            "Cannot be undone"
        ]

    def can_rollback(self) -> bool:
        """ロールバック可能かどうか"""
        return False

    async def rollback(self, execution_result: dict) -> ActionResult:
        """ロールバック処理（オプション）"""
        if not self.can_rollback():
            return ActionResult(
                success=False,
                error="Rollback not supported"
            )
        # ロールバック処理
        return ActionResult(success=True)
```

### 3. アクションのインポート

`backend/app/services/actions/__init__.py` に追加:

```python
from app.services.actions.my_action import MyNewAction
```

### 4. LLM提案システムへの追加

`backend/app/services/actions/proposal.py` のシステムプロンプトに追加:

```python
SYSTEM_PROMPT = """
...
6. my_new_action: 新しいアクションの説明
   Parameters: param1 (type), param2 (type)
...
"""
```

### 5. テストの作成

`backend/tests/test_actions/test_my_action.py`:

```python
import pytest
from app.services.actions.my_action import MyNewAction

@pytest.mark.asyncio
async def test_my_new_action():
    action = MyNewAction({
        "param1": "value1",
        "param2": "value2"
    })

    result = await action.execute()
    assert result.success is True
```

## セキュリティ考慮事項

### 実装されている安全機能

1. **承認フロー**: 全アクション実行前にユーザー承認が必要
2. **Dry-run モード**: 実際の変更前にシミュレーション可能
3. **パラメータ検証**: 不正なパラメータは実行前に拒否
4. **監査ログ**: 全てのアクションは詳細にログ記録
5. **ロールバック**: 一部アクションは取り消し可能

### 開発時の注意点

- **外部APIキー**: 環境変数で管理し、ハードコードしない
- **入力検証**: ユーザー入力は必ず検証する
- **エラーハンドリング**: 詳細なエラー情報を返さない（セキュリティリスク）
- **権限チェック**: 将来的にユーザー権限チェックを実装予定

## トラブルシューティング

### アクションが提案されない

**原因:**
- タスクの情報が不足している
- LLM APIの設定が正しくない

**対処:**
- タスクのタイトルと説明を詳細に記入
- `.env` の `OPENAI_API_KEY` を確認

### アクション実行が失敗する

**原因:**
- 必要な環境変数が設定されていない
- 外部サービスとの接続に問題がある

**対処:**
- ログを確認: `docker-compose logs api`
- 環境変数を確認: `.env` ファイル
- dry-runモードで事前確認

### メール送信ができない

**原因:**
- SMTP設定が未完了

**対処:**
- `.env` に以下を設定:
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your-email@gmail.com
  SMTP_PASSWORD=your-app-password
  ```

## ロードマップ

### 近日実装予定

- [ ] カレンダーイベント作成アクション
- [ ] ファイルアップロード/ダウンロードアクション
- [ ] Slack/Discord通知アクション（現在は手動）
- [ ] GitHub Issues連携アクション

### 将来的な機能

- [ ] アクションチェーン（複数アクションの順次実行）
- [ ] 条件付きアクション（if-then-else）
- [ ] スケジュール実行（cron like）
- [ ] ユーザー権限管理
- [ ] アクションテンプレート

## まとめ

タスクアクションシステムは、単純なタスク管理を超えて、実際の作業を自動化する強力な機能です。安全性を最優先に設計されているため、安心して利用できます。

新しいアクションタイプの追加も簡単なので、自分のワークフローに合わせてカスタマイズしてください。
