import os, zipfile, json, subprocess, shutil, time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

bot = telebot.TeleBot(TOKEN)

BASE_DIR = "hosted_bots"
DATA_FILE = "data.json"
os.makedirs(BASE_DIR, exist_ok=True)

processes = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_owner(message):
    return message.from_user.id == OWNER_ID

def panel():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📤 رفع بوت ZIP", callback_data="upload"))
    kb.add(InlineKeyboardButton("📋 بوتاتي", callback_data="mybots"))
    return kb

def bot_buttons(name):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("▶️ تشغيل", callback_data=f"start:{name}"),
        InlineKeyboardButton("⏹ إيقاف", callback_data=f"stop:{name}")
    )
    kb.add(
        InlineKeyboardButton("📄 اللوگات", callback_data=f"logs:{name}"),
        InlineKeyboardButton("🗑 حذف", callback_data=f"delete:{name}")
    )
    return kb

@bot.message_handler(commands=["start"])
def start(message):
    if not is_owner(message):
        return bot.reply_to(message, "❌ هذا البوت خاص بالمطور فقط.")
    bot.send_message(
        message.chat.id,
        "👋 أهلاً بك في بوت الاستضافة\n\nارفع ملف بوتك بصيغة ZIP ويحتوي:\n`bot.py`\n`requirements.txt`",
        parse_mode="Markdown",
        reply_markup=panel()
    )

@bot.callback_query_handler(func=lambda c: c.data == "upload")
def upload(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📤 ارسل ملف البوت بصيغة ZIP الآن.")

@bot.message_handler(content_types=["document"])
def handle_zip(message):
    if not is_owner(message):
        return

    doc = message.document
    if not doc.file_name.endswith(".zip"):
        return bot.reply_to(message, "❌ ارسل ملف بصيغة zip فقط.")

    bot.reply_to(message, "⏳ جاري رفع وفك الملف...")

    file_info = bot.get_file(doc.file_id)
    downloaded = bot.download_file(file_info.file_path)

    bot_name = doc.file_name.replace(".zip", "").replace(" ", "_")
    bot_dir = os.path.join(BASE_DIR, bot_name)

    if os.path.exists(bot_dir):
        return bot.reply_to(message, "❌ يوجد بوت بنفس الاسم. غيّر اسم الملف.")

    zip_path = f"{bot_name}.zip"
    with open(zip_path, "wb") as f:
        f.write(downloaded)

    os.makedirs(bot_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if ".." in member or member.startswith("/"):
                    raise Exception("ملف ZIP غير آمن")
            z.extractall(bot_dir)
    except Exception as e:
        shutil.rmtree(bot_dir, ignore_errors=True)
        os.remove(zip_path)
        return bot.reply_to(message, f"❌ فشل فك الضغط:\n{e}")

    os.remove(zip_path)

    bot_py = os.path.join(bot_dir, "bot.py")
    req = os.path.join(bot_dir, "requirements.txt")

    if not os.path.exists(bot_py):
        shutil.rmtree(bot_dir, ignore_errors=True)
        return bot.reply_to(message, "❌ لازم داخل ZIP يوجد ملف اسمه bot.py")

    if os.path.exists(req):
        bot.send_message(message.chat.id, "📦 جاري تثبيت المكتبات...")
        subprocess.run(
            ["pip", "install", "-r", req],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    data = load_data()
    data[bot_name] = {
        "path": bot_dir,
        "created": int(time.time()),
        "status": "stopped"
    }
    save_data(data)

    bot.send_message(
        message.chat.id,
        f"✅ تم رفع البوت: `{bot_name}`",
        parse_mode="Markdown",
        reply_markup=bot_buttons(bot_name)
    )

@bot.callback_query_handler(func=lambda c: c.data == "mybots")
def mybots(call):
    bot.answer_callback_query(call.id)
    data = load_data()

    if not data:
        return bot.send_message(call.message.chat.id, "ما عندك بوتات مرفوعة.")

    for name in data:
        bot.send_message(
            call.message.chat.id,
            f"🤖 البوت: `{name}`",
            parse_mode="Markdown",
            reply_markup=bot_buttons(name)
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("start:"))
def start_hosted(call):
    bot.answer_callback_query(call.id)
    name = call.data.split(":", 1)[1]
    data = load_data()

    if name not in data:
        return bot.send_message(call.message.chat.id, "❌ البوت غير موجود.")

    if name in processes and processes[name].poll() is None:
        return bot.send_message(call.message.chat.id, "⚠️ البوت شغال أصلاً.")

    path = data[name]["path"]
    log_path = os.path.join(path, "log.txt")

    log_file = open(log_path, "a", encoding="utf-8")

    p = subprocess.Popen(
        ["python", "bot.py"],
        cwd=path,
        stdout=log_file,
        stderr=log_file
    )

    processes[name] = p
    data[name]["status"] = "running"
    save_data(data)

    bot.send_message(call.message.chat.id, f"✅ تم تشغيل البوت: `{name}`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("stop:"))
def stop_hosted(call):
    bot.answer_callback_query(call.id)
    name = call.data.split(":", 1)[1]

    if name in processes and processes[name].poll() is None:
        processes[name].terminate()
        bot.send_message(call.message.chat.id, f"⏹ تم إيقاف البوت: `{name}`", parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, "⚠️ البوت مو شغال.")

    data = load_data()
    if name in data:
        data[name]["status"] = "stopped"
        save_data(data)

@bot.callback_query_handler(func=lambda c: c.data.startswith("logs:"))
def logs(call):
    bot.answer_callback_query(call.id)
    name = call.data.split(":", 1)[1]
    data = load_data()

    if name not in data:
        return bot.send_message(call.message.chat.id, "❌ غير موجود.")

    log_path = os.path.join(data[name]["path"], "log.txt")

    if not os.path.exists(log_path):
        return bot.send_message(call.message.chat.id, "ماكو لوغات بعد.")

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()[-3500:]

    bot.send_message(call.message.chat.id, f"📄 آخر اللوغات:\n\n```{text}```", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("delete:"))
def delete(call):
    bot.answer_callback_query(call.id)
    name = call.data.split(":", 1)[1]
    data = load_data()

    if name in processes and processes[name].poll() is None:
        processes[name].terminate()

    if name in data:
        shutil.rmtree(data[name]["path"], ignore_errors=True)
        del data[name]
        save_data(data)

    bot.send_message(call.message.chat.id, f"🗑 تم حذف البوت: `{name}`", parse_mode="Markdown")

print("Hosting bot is running...")
bot.infinity_polling()
