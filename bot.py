import asyncio
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    CallbackQueryHandler, filters
)
from datetime import datetime
import os
import nest_asyncio

nest_asyncio.apply()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = '7738451489:AAGLq-xwhNgwfWLp0LOcjMyHQqZ8pItjJ_Q'
ADMIN_ID = 7183009847

REQUIRED_CHANNEL = "@modbeapksfree"
REQUIRED_GROUP = "@modbeapks"

DATA_FILE = "data.json"
LOG_FILE = "logs.txt"
BANNED_FILE = "banned.json"

# Fayllar bazasi
file_db = {}
user_stats = {}
banned_users = set()

# JSON saqlash
def load_data():
    global file_db, user_stats, banned_users
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            file_db.update(data.get("file_db", {}))
            user_stats.update(data.get("user_stats", {}))
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r") as f:
            banned_users.update(json.load(f))

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"file_db": file_db, "user_stats": user_stats}, f)
    with open(BANNED_FILE, "w") as f:
        json.dump(list(banned_users), f)

def log(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} | {message}\n")

def get_sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanal", url="https://t.me/modbeapksfree")],
        [InlineKeyboardButton("👥 Guruh", url="https://t.me/modbeapks")],
        [InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_subs")]
    ])

async def is_subscribed(user_id, context):
    try:
        channel_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        group_member = await context.bot.get_chat_member(REQUIRED_GROUP, user_id)
        return channel_member.status in ['member', 'administrator', 'creator'] and \
               group_member.status in ['member', 'administrator', 'creator']
    except:
        return False

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        return
    await update.message.reply_text(
        "🔐 Botdan foydalanish uchun obuna bo‘ling:",
        reply_markup=get_sub_keyboard()
    )

# Callback tugma — obuna tekshirish
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id in banned_users:
        return
    await query.answer()
    if await is_subscribed(user_id, context):
        await query.edit_message_text("✅ Obuna tasdiqlandi. Endi kalit so‘z yozing:")
    else:
        await query.edit_message_text("❗ Obuna topilmadi. Iltimos, avval kanal va guruhga obuna bo‘ling.")

# Fayl saqlash (faqat admin)
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message = update.message
    file_type = None
    file_id = None

    if message.document:
        file_type = 'document'
        file_id = message.document.file_id
    elif message.video:
        file_type = 'video'
        file_id = message.video.file_id
    elif message.photo:
        file_type = 'photo'
        file_id = message.photo[-1].file_id
    else:
        return

    if message.caption:
        keyword = message.caption.strip().lower()
        file_db[keyword] = {"type": file_type, "id": file_id}
        save_data()
        await message.reply_text(f"✅ Fayl saqlandi: {keyword}")
    else:
        await message.reply_text("❗ Iltimos, caption sifatida kalit so‘z kiriting.")

# Kalit so‘zlar bilan ishlash
async def handle_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id in banned_users:
        return

    keyword = update.message.text.strip().lower()

    log(f"{user_id} | @{user.username} | {keyword}")
    user_stats[str(user_id)] = user_stats.get(str(user_id), 0) + 1
    save_data()

    if not await is_subscribed(user_id, context):
        await update.message.reply_text("🔒 Avval kanal va guruhga obuna bo‘ling:", reply_markup=get_sub_keyboard())
        return

    matched = file_db.get(keyword)
    if matched:
        if matched["type"] == "video":
            await update.message.reply_video(matched["id"])
        elif matched["type"] == "photo":
            await update.message.reply_photo(matched["id"])
        elif matched["type"] == "document":
            await update.message.reply_document(matched["id"])
    else:
        await update.message.reply_text("❗ Bunday kalit so‘z mavjud emas.")

# Statistika (admin)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = f"📊 Foydalanuvchilar soni: {len(user_stats)}\n"
    msg += f"🔑 Kalit so‘zlar soni: {len(file_db)}"
    await update.message.reply_text(msg)

# Loglar (admin)
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            text = f.read()[-4000:]
        await update.message.reply_text(f"📝 Loglar:\n{text}")
    else:
        await update.message.reply_text("Loglar mavjud emas.")

# Ban va unban (admin)
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        user_id = int(context.args[0])
        banned_users.add(user_id)
        save_data()
        await update.message.reply_text(f"🚫 Foydalanuvchi bloklandi: {user_id}")
    else:
        await update.message.reply_text("ID kiriting: /ban 123456789")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        user_id = int(context.args[0])
        banned_users.discard(user_id)
        save_data()
        await update.message.reply_text(f"✅ Ban olib tashlandi: {user_id}")
    else:
        await update.message.reply_text("ID kiriting: /unban 123456789")

# Boshlash
async def main():
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))

    app.add_handler(CallbackQueryHandler(check_subscription))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyword))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, save_file))

    print("✅ Bot ishga tushdi.")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
