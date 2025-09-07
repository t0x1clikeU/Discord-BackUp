# Discord Member Backup Bot

Discord で **ユーザー認証・バックアップ・参加管理** ができる BOT です。  

---

## ⚠️ 注意事項

> このツールは Discord の利用規約に違反する可能性があります。  
> 使用は **自己責任** で行ってください。  
> アカウントの **制限・凍結** のリスクがあります。  

---

## ✅ 主な機能

- **OAuth2 認証**でユーザーを登録
- `/verify <ロール>`  
  認証パネルを表示し、認証後に指定ロールを付与
- `/join <サーバーID>`  
  BOT が入っているサーバーに登録済みユーザーを追加
- `/list`  
  登録済みユーザー数を表示
- `/add-user <ユーザー>`  
  BOT の管理権限を持つユーザーを追加（開発者のみ）
- `/remove-user <ユーザー>`  
  BOT の管理権限を持つユーザーを削除（開発者のみ）

---

## 🧾 必要環境

- Python 3.9+
- ライブラリ  
  ```bash
  pip install discord.py flask pyngrok requests


## 📂 ファイル構成

```
├── main.py                # メインスクリプト
├── verified_users.json    # 認証済みユーザーのデータ
└──allowed_users.json      # 管理者ユーザーのデータ
```

🛠️ 使い方
```
1. Discord Developer Portal の設定

アプリケーションを作成

Bot を作成し、トークンを取得

OAuth2 → Redirects に ngrok で表示される REDIRECT_URI を登録
```
2. 設定ファイルの編集

BOT.py の上部を編集してください：
```
TOKEN = "YOUR_DISCORD_BOT_TOKEN"
CLIENT_ID = 123456789012345678
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
NGROK_AUTHTOKEN = "YOUR_NGROK_AUTHTOKEN"
DEVELOPER_ID = 123456789012345678  # あなたのDiscord ID
```
3. 起動
```
python main.py
```

起動すると ngrok の URL が表示されます。
REDIRECT_URI を Discord Developer Portal に登録してください。


## 🚀 注意点

ngrok を利用しているため、起動のたびに REDIRECT_URI が変わります。

永続的に利用する場合は、VPS や固定ドメインの利用を推奨します。
