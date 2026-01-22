# 外部通知・Webhook統合ガイド

MOSは外部サービス（LINE、Slack、Discord）との連携をサポートしています。外部からタスクを入力し、フォローアップや通知を外部アプリで受け取ることができます。

---

## アーキテクチャ

```
外部入力（LINE/Slack/Discord）
    ↓ Webhook
[ローカルMOS] ← データ保存・処理
    ↓ 通知API
外部出力（同じアプリに通知）
```

### メリット
- **セキュリティ**: データはローカルに保存、外部には出さない
- **利便性**: スマホ・外出先からタスク入力可能
- **通知**: フォローアップを外部アプリで受信
- **認証**: 外部サービスの認証機構を活用

---

## サポートしている機能

### 1. 通知送信（Outgoing）

以下の通知が外部サービスに送信されます：

- **フォローアップ通知**: 朝/昼/夕の定期要約
- **Draft作成通知**: タスク案が生成された時
- **タスクリマインダー**: 期限が近づいた時（将来実装）

### 2. メッセージ受信（Incoming Webhook）

外部サービスからタスクを入力できます：

- **LINE Messaging API**: LINEでタスクを送信
- **Slack Events API**: Slackチャンネルでタスクを送信
- **Discord Bot**: Discord経由でタスクを送信（Bot統合が必要）

---

## セットアップ

### LINE Notify（通知のみ - 最も簡単）

#### 1. トークン取得

1. https://notify-bot.line.me/ にアクセス
2. ログインして「マイページ」へ
3. 「トークンを発行する」をクリック
4. トークン名を入力（例: MOS通知）
5. 通知を送るトークルームを選択
6. トークンをコピー

#### 2. 環境変数設定

```bash
# backend/.env に追加
LINE_NOTIFY_TOKEN=ここにトークンを貼り付け
```

#### 3. 動作確認

```bash
# MOSを再起動
docker-compose restart api

# Webhook状態を確認
curl http://localhost:8000/api/webhook/status
```

#### 4. テスト

フォローアップ時刻になると自動的にLINEに通知が届きます。または：

```bash
# 手動でフォローアップをトリガー
curl -X POST http://localhost:8000/api/followup/trigger \
  -H "Content-Type: application/json" \
  -d '{"period": "morning"}'
```

---

### LINE Messaging API（双方向 - 中級）

LINEでタスクを送信し、通知も受け取れます。

#### 1. LINE Developersで設定

1. https://developers.line.biz/console/ にアクセス
2. 新規プロバイダー作成
3. 新規チャネル作成（Messaging API）
4. 「Webhook URL」を設定:
   ```
   https://あなたのドメイン/api/webhook/line
   ```
5. Channel Secret をコピー
6. Channel Access Token を発行してコピー

#### 2. 環境変数設定

```bash
# backend/.env
LINE_NOTIFY_TOKEN=Channel Access Token
LINE_CHANNEL_SECRET=Channel Secret
```

#### 3. ngrok でローカルテスト（開発時）

```bash
# 別ターミナルで
ngrok http 8000

# 表示されたURLをWebhook URLに設定
# 例: https://abcd1234.ngrok.io/api/webhook/line
```

#### 4. Webhook 有効化

LINE Developers コンソールで「Use webhook」をONにする。

#### 5. テスト

LINEで Bot を友達追加し、メッセージを送信:
```
明日までにレポートを完成させる
```

→ MOSがタスク案を生成し、LINE Notifyで通知が届く

---

### Slack統合

#### 1. Incoming Webhooks設定（通知のみ）

1. Slack ワークスペースで Apps を開く
2. 「Incoming Webhooks」を検索してインストール
3. 通知を送るチャンネルを選択
4. Webhook URL をコピー

```bash
# backend/.env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX
```

#### 2. Events API設定（双方向）

1. Slack API サイト: https://api.slack.com/apps
2. 新規アプリ作成
3. 「Event Subscriptions」を有効化
4. Request URL を設定:
   ```
   https://あなたのドメイン/api/webhook/slack
   ```
5. Subscribe to bot events:
   - `message.channels`
   - `message.groups`
   - `message.im`
6. Signing Secret をコピー

```bash
# backend/.env
SLACK_SIGNING_SECRET=あなたのSigningSecret
```

#### 3. テスト

Slackチャンネルでメッセージを送信:
```
@MOS 明日までにレポートを完成させる
```

---

### Discord統合

#### 1. Webhook設定（通知のみ）

1. Discordサーバー設定を開く
2. 「連携サービス」→「ウェブフック」
3. 「新しいウェブフック」を作成
4. ウェブフックURLをコピー

```bash
# backend/.env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### 2. Bot統合（双方向 - 上級）

Discord Bot統合は別途Botアプリケーションの作成が必要です。

詳細: https://discord.com/developers/docs/intro

---

## API エンドポイント

### Webhook受信

| エンドポイント | 用途 | 認証 |
|--------------|------|------|
| `POST /api/webhook/line` | LINE Messaging API | 署名検証 |
| `POST /api/webhook/slack` | Slack Events API | 署名検証 |
| `POST /api/webhook/discord` | Discord Bot | - |
| `GET /api/webhook/status` | 設定状態確認 | なし |

### Webhook状態確認

```bash
curl http://localhost:8000/api/webhook/status
```

レスポンス例:
```json
{
  "configured_providers": ["line_notify", "slack"],
  "line_webhook_enabled": true,
  "slack_webhook_enabled": false
}
```

---

## トラブルシューティング

### 通知が届かない

**原因1: トークン未設定**
```bash
# .envファイルを確認
cat backend/.env | grep -E '(LINE|SLACK|DISCORD)'

# APIを再起動
docker-compose restart api
```

**原因2: ネットワークエラー**

ログを確認:
```bash
docker-compose logs api | grep -i notification
```

**原因3: トークンが無効**

トークンを再発行して設定し直す。

---

### Webhookが動作しない

**原因1: Webhook URLが間違っている**

ngrokを使っている場合、再起動すると URL が変わるので注意。

**原因2: 署名検証エラー**

```bash
# ログを確認
docker-compose logs api | grep -i "Invalid.*signature"

# Channel Secretが正しいか確認
echo $LINE_CHANNEL_SECRET
```

**原因3: ファイアウォール**

ローカル開発の場合、ngrokを使用してください:
```bash
ngrok http 8000
```

---

### LINE Bot が応答しない

**チェックリスト:**
1. Webhook URLが正しく設定されているか
2. LINE Developers コンソールで「Webhook」がONになっているか
3. Channel Secret と Access Token が正しいか
4. Bot を友達追加しているか
5. ngrok が起動しているか（ローカル開発時）

**テスト方法:**
```bash
# Webhook URLにテストリクエストを送信（LINE Console）
# または curl でテスト
curl -X POST http://localhost:8000/api/webhook/line \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "type": "message",
      "message": {"type": "text", "text": "テスト"},
      "source": {"userId": "test"}
    }]
  }'
```

---

## セキュリティ

### 署名検証

外部からのWebhookリクエストは署名検証されます：

- **LINE**: `X-Line-Signature` ヘッダーで HMAC-SHA256 検証
- **Slack**: `X-Slack-Signature` ヘッダーで HMAC-SHA256 検証

署名検証が失敗すると`401 Unauthorized`が返されます。

### 推奨事項

1. **シークレットを環境変数で管理**: コードにハードコードしない
2. **HTTPS使用**: 本番環境では必ずHTTPSを使用
3. **ngrokは開発のみ**: 本番では使用しない
4. **トークンの定期的なローテーション**: セキュリティのため定期的に再発行

---

## 本番環境デプロイ

### 必要なもの

1. **公開ドメイン**: Webhook URL用（HTTPS必須）
2. **環境変数設定**: シークレット・トークンの安全な管理
3. **リバースプロキシ**: nginx / Caddy / Traefik
4. **SSL証明書**: Let's Encrypt推奨

### 推奨構成

```
インターネット
    ↓ HTTPS
[リバースプロキシ（nginx）]
    ↓ HTTP
[Docker: MOS Backend]
    ↓
[PostgreSQL, Redis]
```

### nginx設定例

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /api/webhook/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 開発ロードマップ

### 実装済み
- ✅ LINE Notify通知
- ✅ Slack Webhook通知
- ✅ Discord Webhook通知
- ✅ LINE Messaging API Webhook受信
- ✅ Slack Events API Webhook受信
- ✅ フォローアップ通知統合
- ✅ Draft作成通知統合

### 今後の拡張
- [ ] タスクリマインダー通知
- [ ] インタラクティブなボタン（LINE/Slack）
- [ ] リッチメッセージフォーマット
- [ ] メール通知統合
- [ ] Telegram統合
- [ ] 通知設定UI（フロントエンド）

---

## まとめ

外部通知・Webhook統合により、MOSを以下のように使用できます：

1. **外出先からタスク入力**: LINEやSlackでタスクを送信
2. **フォローアップ受信**: 定期的な要約を外部アプリで確認
3. **データはローカル保存**: セキュリティを維持しつつ利便性向上

設定は簡単で、LINE Notifyなら5分で完了します。

質問や問題がある場合は、GitHub Issuesで報告してください。
