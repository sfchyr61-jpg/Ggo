
import os
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "PUT_YOUR_TOKEN_HERE"
OWNER_ID = 8065884629
CHANNEL = "@OxfordMulhdeen"

BOOKS_FILE = "books.json"
USERS_FILE = "users.json"

user_states = {}

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

books = load_json(BOOKS_FILE, {
    "فلسفة": {},
    "أديان": {},
    "تاريخ": {}
})

users = load_json(USERS_FILE, [])

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in [u["id"] for u in users]:
        users.append({
            "id": user.id,
            "name": user.full_name,
            "username": user.username
        })
        save_json(USERS_FILE, users)

        try:
            await context.bot.send_message(
                OWNER_ID,
                f"📥 مستخدم جديد دخل البوت\n\n"
                f"👤 الاسم: {user.full_name}\n"
                f"🆔 الآيدي: {user.id}\n"
                f"👤 اليوزر: @{user.username}" if user.username else
                f"📥 مستخدم جديد دخل البوت\n\n👤 الاسم: {user.full_name}\n🆔 الآيدي: {user.id}\n👤 اليوزر: لا يوجد"
            )
        except:
            pass

    if not await is_subscribed(context.bot, user.id):
        kb = [[InlineKeyboardButton("📢 القناة", url=f"https://t.me/{CHANNEL.replace('@','')}")]]
        await update.message.reply_text(
            "يجب الاشتراك بالقناة أولاً",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    buttons = [[InlineKeyboardButton(cat, callback_data=f"cat:{cat}")] for cat in books]

    if user.id == OWNER_ID:
        buttons += [
            [InlineKeyboardButton("➕ إضافة كتاب", callback_data="add_book")],
            [InlineKeyboardButton("❌ حذف كتاب", callback_data="delete_book")],
            [InlineKeyboardButton("👥 المستخدمون", callback_data="users")]
        ]

    await update.message.reply_text(
        "📚 اختر القسم",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global books

    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data.startswith("cat:"):
        cat = data.split(":",1)[1]

        rows = []
        for name in books.get(cat, {}):
            rows.append([InlineKeyboardButton(name, callback_data=f"book:{cat}:{name}")])

        rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="home")])

        await q.message.edit_text(cat, reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("book:"):
        _, cat, name = data.split(":",2)
        file_id = books[cat][name]
        await context.bot.send_document(uid, file_id, caption=name)

    elif data == "home":
        buttons = [[InlineKeyboardButton(cat, callback_data=f"cat:{cat}")] for cat in books]

        if uid == OWNER_ID:
            buttons += [
                [InlineKeyboardButton("➕ إضافة كتاب", callback_data="add_book")],
                [InlineKeyboardButton("❌ حذف كتاب", callback_data="delete_book")],
                [InlineKeyboardButton("👥 المستخدمون", callback_data="users")]
            ]

        await q.message.edit_text("📚 اختر القسم", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "users" and uid == OWNER_ID:
        text = f"👥 عدد المستخدمين: {len(users)}\n\n"
        for u in users:
            text += f"👤 {u['name']}\n🆔 {u['id']}\n\n"
        await q.message.reply_text(text[:4000])

    elif data == "add_book" and uid == OWNER_ID:
        user_states[uid] = {"step": "choose_cat_add"}

        rows = [[InlineKeyboardButton(c, callback_data=f"addcat:{c}")] for c in books]
        await q.message.reply_text("اختر القسم")

    elif data.startswith("addcat:") and uid == OWNER_ID:
        cat = data.split(":",1)[1]
        user_states[uid] = {"step": "send_file", "cat": cat}
        await q.message.reply_text("ارسل ملف الكتاب")

    elif data == "delete_book" and uid == OWNER_ID:
        rows = [[InlineKeyboardButton(c, callback_data=f"delcat:{c}")] for c in books]
        await q.message.reply_text("اختر القسم للحذف", reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("delcat:") and uid == OWNER_ID:
        cat = data.split(":",1)[1]

        rows = [
            [InlineKeyboardButton(name, callback_data=f"delbook:{cat}:{name}")]
            for name in books.get(cat, {})
        ]

        await q.message.reply_text("اختر الكتاب", reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("delbook:") and uid == OWNER_ID:
        _, cat, name = data.split(":",2)

        if name in books[cat]:
            del books[cat][name]
            save_json(BOOKS_FILE, books)

        await q.message.reply_text("✅ تم حذف الكتاب")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid != OWNER_ID:
        return

    state = user_states.get(uid)

    if not state or state.get("step") != "send_file":
        return

    state["file_id"] = update.message.document.file_id
    state["step"] = "book_name"

    await update.message.reply_text("ارسل اسم الكتاب")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global books

    uid = update.effective_user.id

    if uid != OWNER_ID:
        return

    state = user_states.get(uid)

    if not state:
        return

    if state.get("step") == "book_name":
        name = update.message.text
        cat = state["cat"]
        books.setdefault(cat, {})[name] = state["file_id"]
        save_json(BOOKS_FILE, books)

        user_states.pop(uid, None)

        await update.message.reply_text("✅ تم إضافة الكتاب")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()
