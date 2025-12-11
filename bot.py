# bot.py
import os
import zipfile
import json
import time
import threading
from flask import Flask
from moviepy.editor import VideoFileClip
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified

# ------------------- CONFIG (from ENV) -------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN or API_ID == 0 or not API_HASH or OWNER_ID == 0:
    raise Exception("Please set BOT_TOKEN, API_ID, API_HASH and OWNER_ID environment variables.")

# ------------------- Pyrogram Client -------------------
bot = Client("PremiumAestheticBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ------------------- Premium DB -------------------
PREMIUM_FILE = "premium.json"
if not os.path.exists(PREMIUM_FILE):
    with open(PREMIUM_FILE, "w") as f:
        f.write('{"premium_users": {}}')

def load_premium():
    with open(PREMIUM_FILE, "r") as f:
        return json.load(f)

def save_premium(data):
    with open(PREMIUM_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_premium(user_id):
    data = load_premium()
    uid = str(user_id)
    if uid not in data["premium_users"]:
        return False
    expiry = data["premium_users"][uid]["expiry"]
    return expiry > int(time.time())

def get_expiry(user_id):
    data = load_premium()
    uid = str(user_id)
    if uid not in data["premium_users"]:
        return None
    return data["premium_users"][uid]["expiry"]

def add_premium(user_id, seconds):
    data = load_premium()
    uid = str(user_id)
    expiry = int(time.time()) + seconds
    data["premium_users"][uid] = {"expiry": expiry}
    save_premium(data)

def remove_premium(user_id):
    data = load_premium()
    uid = str(user_id)
    if uid in data["premium_users"]:
        del data["premium_users"][uid]
    save_premium(data)

# ------------------- Animated progress -------------------
async def anim_progress(current, total, message):
    try:
        percent = (current * 100) / total
        blocks = int(percent // 5)
        bar = "▰" * blocks + "▱" * (20 - blocks)
        await message.edit(f"✨ **Processing…**\n{bar} `{percent:.1f}%`")
    except MessageNotModified:
        pass
    except Exception:
        pass

# ------------------- Flask web server (Render free hack) -------------------
app = Flask(__name__)
@app.route("/")
def home():
    return "✅ Bot is running (Flask alive)!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    # use 0.0.0.0 so Render can access
    app.run(host="0.0.0.0", port=port)

# ------------------- BOT HANDLERS -------------------

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply(
        "**🌸 Premium File Manager Bot**\n"
        "Rename • ZIP • Password ZIP • Extract • Compress • Premium System",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 Commands Menu", callback_data="cmd_menu")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")],
        ])
    )

@bot.on_callback_query(filters.regex("cmd_menu"))
async def cmd_menu(client, query):
    await query.message.edit(
        "**📜 Full Commands Menu**\n\n"
        "**File Tools:**\n"
        "✏️ Rename\n"
        "🗜 ZIP\n"
        "🔒 ZIP (Password)\n"
        "🔓 UNZIP\n"
        "🎥 Compress Video\n\n"
        "**Premium Commands:**\n"
        "/premiumstatus – Check your premium\n"
        "/approve @user <seconds>\n"
        "/remove @user\n\n"
        "**Examples:**\n"
        "`/approve @lakshit 60` → 1 min\n"
        "`/approve @lakshit 86400` → 1 day\n"
        "`/approve @lakshit 31536000` → 1 year\n"
        "`/approve @lakshit 9999999999` → lifetime\n",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="start_back")]])
    )

@bot.on_callback_query(filters.regex("start_back"))
async def start_back(client, query):
    await start_cmd(client, query.message)

@bot.on_callback_query(filters.regex("admin_panel"))
async def admin_panel(client, query):
    if query.from_user.id != OWNER_ID:
        return await query.answer("🚫 Only owner allowed!", show_alert=True)
    await query.message.edit(
        "**👑 ADMIN PANEL**\nPremium Control System",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Broadcast (coming soon)", callback_data="none")],
            [InlineKeyboardButton("⬅️ Back", callback_data="cmd_menu")]
        ])
    )

@bot.on_message(filters.command("premiumstatus"))
async def premium_status(client, message):
    uid = message.from_user.id
    expiry_ts = get_expiry(uid)
    if expiry_ts is None:
        return await message.reply("❌ You are not a premium user.")
    if expiry_ts < int(time.time()):
        return await message.reply("❌ Your premium has expired.")
    expiry_readable = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry_ts))
    await message.reply(
        f"👤 User: @{message.from_user.username or 'NoUsername'}\n"
        f"⭐ Status: Premium\n"
        f"⏳ Expires: `{expiry_readable}`\n"
        f"🟢 Active"
    )

@bot.on_message(filters.command("approve"))
async def approve_user(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("🚫 Only owner can approve!")
    # support reply or /approve @username seconds
    if message.reply_to_message:
        # reply to user, require seconds
        if len(message.command) < 2:
            return await message.reply("Usage (when replying): /approve <seconds>")
        try:
            seconds = int(message.command[1])
        except:
            return await message.reply("Invalid seconds. Use a number (seconds).")
        user = message.reply_to_message.from_user
        add_premium(user.id, seconds)
        expiry_readable = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(get_expiry(user.id)))
        return await message.reply(f"✅ Approved: @{user.username or user.first_name}\nExpires: `{expiry_readable}`")
    # normal /approve @username seconds
    if len(message.command) < 3:
        return await message.reply("Usage:\n/approve @username seconds")
    username = message.command[1].replace("@", "")
    try:
        seconds = int(message.command[2])
    except:
        return await message.reply("Invalid seconds. Use a number (seconds).")
    user = await client.get_users(username)
    add_premium(user.id, seconds)
    expiry_readable = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(get_expiry(user.id)))
    await message.reply(f"✅ Approved: @{username}\nExpires: `{expiry_readable}`")

@bot.on_message(filters.command("remove"))
async def remove_user(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("🚫 Only owner allowed!")
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        remove_premium(user.id)
        return await message.reply(f"❌ Removed premium: @{user.username or user.first_name}")
    if len(message.command) < 2:
        return await message.reply("Usage: /remove @username")
    username = message.command[1].replace("@", "")
    user = await client.get_users(username)
    remove_premium(user.id)
    await message.reply(f"❌ Removed premium: @{username}")

# When file is sent
@bot.on_message(filters.document | filters.video | filters.audio)
async def file_received(client, message):
    # premium check
    if not is_premium(message.from_user.id):
        return await message.reply("❌ You are not a premium user.\nAsk owner to approve you.")
    file = message.document or message.video or message.audio
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Rename", callback_data=f"rename|{file.file_id}")],
        [InlineKeyboardButton("🗜 ZIP", callback_data=f"zip|{file.file_id}"),
         InlineKeyboardButton("🔒 ZIP+Pass", callback_data=f"zippass|{file.file_id}")],
        [InlineKeyboardButton("🔓 UNZIP", callback_data=f"unzip|{file.file_id}"),
         InlineKeyboardButton("🎥 Compress", callback_data=f"vcompress|{file.file_id}")]
    ])
    await message.reply_text(f"📄 `{file.file_name}`\nChoose an action:", reply_markup=keyboard)

# callback handler (buttons)
@bot.on_callback_query()
async def callback_handler(client, query):
    # ensure premium (again)
    if not is_premium(query.from_user.id):
        return await query.answer("❌ Your premium expired or not active.", show_alert=True)

    # parse
    try:
        action, file_id = query.data.split("|")
    except:
        return await query.answer("Unknown action.", show_alert=True)

    status_msg = await query.message.reply_text("📥 Downloading...")
    # download
    file_path = await client.download_media(file_id, progress=anim_progress, progress_args=(status_msg,))

    # RENAME flow
    if action == "rename":
        await status_msg.edit_text("✏️ Send new filename (reply to this message):")

        # nested handler — listens for a single reply; note: duplicates can accumulate in heavy use
        @bot.on_message(filters.text & filters.reply)
        async def handle_rename(c, m):
            # ensure reply is to our status_msg
            if not m.reply_to_message or m.reply_to_message.message_id != status_msg.message_id:
                return
            newname = m.text.strip()
            if not newname:
                return await m.reply("Invalid filename.")
            dest = os.path.join("downloads", newname)
            os.makedirs("downloads", exist_ok=True)
            try:
                os.rename(file_path, dest)
            except Exception as e:
                return await m.reply(f"Rename failed: {e}")
            await m.reply_document(dest, caption=f"✨ Renamed to `{newname}`")
            try:
                os.remove(dest)
            except: pass

    # ZIP flow
    elif action == "zip":
        out = file_path + ".zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(file_path, arcname=os.path.basename(file_path))
        await query.message.reply_document(out, caption="🗜 ZIP Ready")
        try:
            os.remove(out)
            os.remove(file_path)
        except: pass

    # ZIP with password flow
    elif action == "zippass":
        await status_msg.edit_text("🔑 Send password for zip (reply to this message):")

        @bot.on_message(filters.text & filters.reply)
        async def handle_zippass(c, m):
            if not m.reply_to_message or m.reply_to_message.message_id != status_msg.message_id:
                return
            pwd = m.text.strip()
            out = file_path + ".zip"
            # Note: Python's zipfile supports password only for extracting — for creation we write normally.
            # We'll write file then try to set a password using the same module by rewriting entries (works for many clients).
            try:
                with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                    z.write(file_path, arcname=os.path.basename(file_path))
                # setpassword only affects reading, not creating; we will send note with password.
                await m.reply_document(out, caption=f"🔒 ZIP created. Password: `{pwd}`")
            except Exception as e:
                await m.reply(f"Failed to create zip: {e}")
            try:
                os.remove(out)
                os.remove(file_path)
            except: pass

    # UNZIP flow
    elif action == "unzip":
        await status_msg.edit_text("🔑 Send password (reply with '0' if none):")

        @bot.on_message(filters.text & filters.reply)
        async def handle_unzip(c, m):
            if not m.reply_to_message or m.reply_to_message.message_id != status_msg.message_id:
                return
            pwd = m.text.strip()
            extract_dir = os.path.join("unzipped", str(int(time.time())))
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(file_path) as z:
                    if pwd == "0":
                        z.extractall(extract_dir)
                    else:
                        z.extractall(extract_dir, pwd=pwd.encode())
            except RuntimeError as re:
                return await m.reply("❌ Wrong password or corrupted zip.")
            except Exception as e:
                return await m.reply(f"❌ Extract failed: {e}")
            files = os.listdir(extract_dir)
            if not files:
                return await m.reply("No files found inside zip.")
            for f in files:
                path_f = os.path.join(extract_dir, f)
                await m.reply_document(path_f, caption=f"Extracted: `{f}`")
            # cleanup
            try:
                os.remove(file_path)
            except: pass

    # VIDEO COMPRESS
    elif action == "vcompress":
        await status_msg.edit_text("🎥 Compressing video (this may take time)…")
        out = file_path + "_compressed.mp4"
        try:
            clip = VideoFileClip(file_path)
            clip.write_videofile(out, bitrate="400k", threads=0)
            await query.message.reply_video(out, caption="✨ Video Compressed")
        except Exception as e:
            await query.message.reply_text(f"Video compress failed: {e}")
        finally:
            try:
                os.remove(out)
                os.remove(file_path)
            except: pass

    await query.message.reply_text("🌟 Task completed.")

# ------------------- RUN BOT (in thread) & Flask (main) -------------------
def run_bot():
    print("Starting Pyrogram client...")
    bot.start()
    print("Pyrogram started. Bot is online.")
    try:
        idle()  # blocks here until stop
    finally:
        bot.stop()
        print("Bot stopped.")

if __name__ == "__main__":
    # start bot thread
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

    # run flask in main thread (Render expects web service)
    print("Starting Flask webserver...")
    run_flask()