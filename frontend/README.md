# MOS Frontend

MOSのフロントエンドアプリケーション（Next.js App Router + TypeScript + Tailwind CSS）

## 技術スタック

- **Next.js 14**: React フレームワーク（App Router）
- **TypeScript**: 型安全性
- **Tailwind CSS**: ユーティリティファーストCSS
- **React Query**: データフェッチングとキャッシュ
- **Axios**: HTTPクライアント
- **Lucide React**: アイコンライブラリ
- **date-fns**: 日付フォーマット

## ローカル開発

### 前提条件

- Node.js 20+
- npm

### セットアップ

```bash
cd frontend

# 依存関係をインストール
npm install

# 環境変数を設定
cp .env.example .env
# .envを編集してAPIのURLを設定

# 開発サーバーを起動
npm run dev
```

アプリケーションは http://localhost:3000 で起動します。

### 利用可能なスクリプト

```bash
npm run dev         # 開発サーバー起動
npm run build       # プロダクションビルド
npm run start       # プロダクションサーバー起動
npm run lint        # ESLint実行
npm run type-check  # TypeScriptの型チェック
```

## Docker

```bash
# イメージをビルド
docker build -t mos-frontend .

# コンテナを起動
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 mos-frontend
```

## プロジェクト構造

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── layout.tsx    # ルートレイアウト
│   │   ├── page.tsx      # ホーム（チャット）
│   │   ├── tasks/        # タスク一覧
│   │   ├── drafts/       # Draft承認
│   │   ├── projects/     # プロジェクト管理
│   │   └── followup/     # フォローアップ
│   ├── components/       # 再利用可能なコンポーネント
│   ├── lib/              # ユーティリティとAPI クライアント
│   └── types/            # TypeScript型定義
├── public/               # 静的ファイル
└── package.json
```

## 主要な機能

### 1. チャット（ホーム）

- タスクを自然な言葉で入力
- LLMがタスク案を生成
- メッセージ履歴の表示

### 2. タスク管理

- タスク一覧（カンバン形式）
- ステータス変更（TODO → 進行中 → 完了）
- 優先度・期限の表示

### 3. Draft承認

- LLMが生成したタスク案の一覧
- Accept（承認）/ Reject（拒否）

### 4. プロジェクト

- プロジェクト一覧
- プロジェクトごとのタスク管理

### 5. フォローアップ

- 朝/昼/夕の定期要約
- タスクの進捗状況

## API連携

バックエンドAPIとの通信は `src/lib/api.ts` で実装されています。

```typescript
import { apiClient } from "@/lib/api";

// タスク一覧取得
const tasks = await apiClient.getTasks();

// メッセージ送信
const result = await apiClient.sendMessage({ content: "タスクの内容" });
```

## 環境変数

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## トラブルシューティング

### APIに接続できない

1. バックエンドが起動しているか確認
2. `.env`ファイルの`NEXT_PUBLIC_API_URL`が正しいか確認
3. CORSの設定を確認

### ビルドエラー

```bash
# キャッシュをクリア
rm -rf .next node_modules
npm install
npm run build
```

## 今後の拡張

- [ ] タスク作成・編集フォーム
- [ ] プロジェクト作成・編集
- [ ] フィルタリング・検索機能
- [ ] ダークモード
- [ ] モバイル対応の改善
- [ ] 認証機能

## ライセンス

このプロジェクトはMOSプロジェクトの一部です。
