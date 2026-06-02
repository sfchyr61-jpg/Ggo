import asyncio, os, sys, time, random, sqlite3, re, shutil, logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant, ChatAdminRequired
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.stream import StreamAudioEnded
from pytgcalls.exceptions import NoActiveGroupCall, GroupCallNotFound
from yt_dlp import YoutubeDL
from functools import wraps
import config

# ================== Logging ==================
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if shutil.which("ffmpeg") is None:
    logger.critical("ffmpeg غير مثبت!")

# ================== DB ==================
DB_PATH = "music_bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sudo_users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS queues (
                    chat_id INTEGER,
                    position INTEGER,
                    query TEXT,
                    PRIMARY KEY (chat_id, position)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS playback_state (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    file_path TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS force_sub (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    channel TEXT,
                    enabled INTEGER DEFAULT 0
                )''')
    c.execute('''INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_name', ?)''', (config.BOT_NAME,))
    conn.commit()
    conn.close()

def load_sudo():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM sudo_users")
    rows = c.fetchall()
    conn.close()
    return {row[0] for row in rows}

def save_sudo(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sudo_users (user_id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()

def remove_sudo_db(uid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sudo_users WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()

def get_bot_name():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key='bot_name'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else config.BOT_NAME

def set_bot_name_db(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('bot_name', ?)", (name,))
    conn.commit()
    conn.close()

def save_queue_sync(chat_id, queue_list):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("BEGIN")
        c.execute("DELETE FROM queues WHERE chat_id=?", (chat_id,))
        for i, q in enumerate(queue_list):
            c.execute("INSERT INTO queues (chat_id, position, query) VALUES (?,?,?)", (chat_id, i, q))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

def load_queue_sync(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT query FROM queues WHERE chat_id=? ORDER BY position", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def clear_queue_sync(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def save_playback_state(chat_id, title, file_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO playback_state (chat_id, title, file_path) VALUES (?,?,?)",
              (chat_id, title, file_path))
    conn.commit()
    conn.close()

def clear_playback_state(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM playback_state WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def load_all_playback_states():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id, title, file_path FROM playback_state")
    rows = c.fetchall()
    conn.close()
    return rows

def set_force_sub(channel, enabled):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO force_sub (id, channel, enabled) VALUES (1, ?, ?)",
              (channel, int(enabled)))
    conn.commit()
    conn.close()

def get_force_sub():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT channel, enabled FROM force_sub WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row if row else (None, 0)

init_db()
SUDO_USERS = load_sudo()
bot_name = get_bot_name()

# ================== Clients ==================
bot = Client("MusicBot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)
assistant = Client("AssistantAccount", api_id=config.API_ID, api_hash=config.API_HASH, session_string=config.STRING_SESSION)
call_py = PyTgCalls(assistant)

ACTIVATED_CHATS = set()
current_song = {}
locks = {}
queues = {}
song_ended_flags = {}
last_play_time = {}
BOT_USERNAME = None

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_DOWNLOADS = 10
download_sem = asyncio.Semaphore(MAX_DOWNLOADS)

broadcast_queue = asyncio.Queue()
broadcast_worker_task = None

# ================== yt-dlp ==================
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": f"{DOWNLOADS_DIR}/%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "nocheckcertificate": True,
    "geo_bypass": True,
    "socket_timeout": 30,
    "retries": 3,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }] if shutil.which("ffmpeg") else [],
}

def find_audio_file(identifier):
    try:
        for f in os.listdir(DOWNLOADS_DIR):
            if identifier in f and f.endswith(('.mp3', '.m4a', '.opus', '.webm')):
                return os.path.join(DOWNLOADS_DIR, f)
    except Exception:
        pass
    return None

def search_and_download(query, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                if re.match(r'https?://', query):
                    info = ydl.extract_info(query, download=True)
                else:
                    info = ydl.extract_info(f"ytsearch:{query}", download=True)["entries"][0]
                file_id = info.get("id")
                filename = find_audio_file(file_id)
                if not filename:
                    filename = ydl.prepare_filename(info)
                    filename = re.sub(r'\.(webm|m4a|opus)$', '.mp3', filename)
                    if not os.path.exists(filename):
                        filename = find_audio_file(file_id)
                return filename, info.get("title", "Unknown"), None
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Download attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return None, None, last_error

# ================== صلاحيات & اشتراك ==================
def is_admin(client, message):
    if message.chat.type not in ("group", "supergroup"):
        return True
    user_id = message.from_user.id
    if user_id == config.OWNER_ID or user_id in SUDO_USERS:
        return True
    try:
        member = message.chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def check_force_sub(client, user_id):
    channel, enabled = get_force_sub()
    if not enabled or not channel:
        return True
    try:
        member = await client.get_chat_member(channel, user_id)
        if member.status in ("left", "kicked"):
            return False
        return True
    except (UserNotParticipant, ChatAdminRequired):
        # إذا كان البوت ليس مشرفاً في القناة، نسمح بالمرور (يمكن إعلام المالك لاحقاً)
        return True
    except Exception:
        return True

async def force_sub_message(chat_id, channel):
    channel_username = channel.replace("@", "")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اشترك بالقناة", url=f"https://t.me/{channel_username}")],
        [InlineKeyboardButton("🔄 تحقق مجدد", callback_data="check_sub")]
    ])
    try:
        await bot.send_message(chat_id, "⚠️ يجب الاشتراك بالقناة أولاً لتشغيل البوت", reply_markup=keyboard)
    except Exception:
        pass

def admin_required(func):
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if not is_admin(client, message):
            return await message.reply_text("⚠️ يجب أن تكون مشرفاً لاستخدام هذا الأمر.")
        if not await check_force_sub(client, message.from_user.id):
            channel, _ = get_force_sub()
            return await force_sub_message(message.chat.id, channel)
        user_id = message.from_user.id
        now = time.time()
        if user_id in last_play_time and now - last_play_time[user_id] < 5:
            return await message.reply_text("⏳ انتظر قليلاً قبل التشغيل مجدداً.")
        last_play_time[user_id] = now
        return await func(client, message, *args, **kwargs)
    return wrapper

async def get_lock(chat_id):
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    return locks[chat_id]

async def get_queue(chat_id):
    if chat_id not in queues:
        q = asyncio.Queue()
        saved = load_queue_sync(chat_id)
        for item in saved:
            await q.put(item)
        queues[chat_id] = q
    return queues[chat_id]

# ================== تشغيل وانضمام ==================
async def safe_join_and_play(chat_id, file_path, title):
    try:
        await call_py.join_group_call(chat_id, AudioPiped(file_path))
        current_song[chat_id] = {"title": title, "file": file_path}
        save_playback_state(chat_id, title, file_path)
        return True
    except (NoActiveGroupCall, GroupCallNotFound):
        return False
    except Exception as e:
        logger.error(f"Play error: {e}")
        return False

async def play_next(chat_id):
    lock = await get_lock(chat_id)
    async with lock:
        if song_ended_flags.get(chat_id, False):
            return
        song_ended_flags[chat_id] = True

        q = await get_queue(chat_id)
        if not q.empty():
            next_query = await q.get()
            items = []
            while not q.empty():
                items.append(await q.get())
            for item in items:
                await q.put(item)
            save_queue_sync(chat_id, items)
            await start_playing(chat_id, next_query)
        else:
            if chat_id in current_song:
                file_path = current_song[chat_id].get("file")
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                del current_song[chat_id]
            clear_playback_state(chat_id)
            try:
                await call_py.leave_group_call(chat_id)
            except Exception:
                pass
            song_ended_flags.pop(chat_id, None)

async def start_playing(chat_id, query):
    lock = await get_lock(chat_id)
    async with lock:
        if chat_id in current_song:
            q = await get_queue(chat_id)
            await q.put(query)
            items = []
            temp_q = asyncio.Queue()
            while not q.empty():
                item = await q.get()
                items.append(item)
                await temp_q.put(item)
            while not temp_q.empty():
                await q.put(await temp_q.get())
            save_queue_sync(chat_id, items)
            await bot.send_message(chat_id, f"✅ تمت إضافة `{query}` إلى قائمة الانتظار.")
            return

        msg = await bot.send_message(chat_id, f"⏳ جارٍ تحميل `{query}`...")
        loop = asyncio.get_running_loop()
        try:
            # تنفيذ التحميل مع timeout 60 ثانية
            future = loop.run_in_executor(None, search_and_download, query)
            file_path, title, error = await asyncio.wait_for(future, timeout=60)
        except asyncio.TimeoutError:
            await msg.edit("❌ انتهت مهلة التحميل. حاول مجدداً.")
            return
        if not file_path:
            error_msg = f"❌ فشل التحميل: {error}" if error else "❌ فشل التحميل. تأكد من الرابط أو الاسم."
            await msg.edit(error_msg)
            return

        success = await safe_join_and_play(chat_id, file_path, title)
        if success:
            await msg.edit(f"🎶 الآن شغال: **{title}**")
            song_ended_flags[chat_id] = False
        else:
            await msg.edit("❌ لا يمكن بدء المكالمة الصوتية. تأكد من صلاحية المجموعة.")
            if os.path.exists(file_path):
                os.remove(file_path)

# ================== حدث انتهاء البث ==================
@call_py.on_stream_end()
async def on_stream_end(client, update: Update):
    if isinstance(update, StreamAudioEnded):
        chat_id = update.chat_id
        if chat_id in current_song:
            file_path = current_song[chat_id].get("file")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            del current_song[chat_id]
        clear_playback_state(chat_id)
        await play_next(chat_id)

# ================== /start واجهات ==================
async def get_bot_username():
    global BOT_USERNAME
    if not BOT_USERNAME:
        try:
            me = await bot.get_me()
            BOT_USERNAME = me.username
        except Exception:
            pass
    return BOT_USERNAME

async def send_start_interface(message, user_id):
    username = await get_bot_username()
    add_url = f"https://t.me/{username}?startgroup=true" if username else "https://t.me/"
    if user_id == config.OWNER_ID:
        text = f"👑 مالك البوت {bot_name}\n\n⚡ لوحة التحكم الكاملة"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ رفع مطور", callback_data="add_sudo"),
             InlineKeyboardButton("➖ تنزيل مطور", callback_data="del_sudo")],
            [InlineKeyboardButton("👥 قائمة المطورين", callback_data="sudo_list"),
             InlineKeyboardButton("📊 إحصائيات", callback_data="bot_info")],
            [InlineKeyboardButton("🔄 إعادة تشغيل", callback_data="restart_bot"),
             InlineKeyboardButton("📢 إذاعة", callback_data="broadcast_owner")],
            [InlineKeyboardButton("✏️ تعيين اسم", callback_data="set_name")],
            [InlineKeyboardButton("🔐 تفعيل الاشتراك", callback_data="set_force_on"),
             InlineKeyboardButton("🔓 تعطيل الاشتراك", callback_data="set_force_off")]
        ])
    elif user_id in SUDO_USERS:
        text = "⚡ مطور معتمد"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 تشغيل", callback_data="dev_play"),
             InlineKeyboardButton("📊 إحصائيات", callback_data="dev_stats")],
            [InlineKeyboardButton("📢 إذاعة", callback_data="dev_broadcast")]
        ])
    else:
        text = (
            f"🎵 **{bot_name}**\n\n"
            "• بوت ميوزك احترافي\n"
            "• يدعم YouTube, SoundCloud, Spotify\n"
            "• أضفه لمجموعتك وابدأ التشغيل"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ اضفني", url=add_url)],
            [InlineKeyboardButton("📖 الأوامر", callback_data="user_help")],
            [InlineKeyboardButton("👨🏻‍💻 المطور", url="https://t.me/DowzC")]
        ])
    if hasattr(message, 'edit_text'):
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await message.reply_text(text, reply_markup=keyboard)
    else:
        await message.reply_text(text, reply_markup=keyboard)

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    await send_start_interface(message, message.from_user.id)

# ================== أوامر المجموعات ==================
@bot.on_message(filters.command(["شغل", "play"]) & filters.group)
@admin_required
async def play_command(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("🎧 اكتب اسم الأغنية أو الرابط. مثال: /شغل imagine dragons")
    query = message.text.split(None, 1)[1]
    chat_id = message.chat.id
    ACTIVATED_CHATS.add(chat_id)
    await start_playing(chat_id, query)

@bot.on_message(filters.command("تخطي") & filters.group)
@admin_required
async def skip_command(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in current_song:
        return await message.reply_text("لا يوجد شيء يعمل الآن.")
    # تخطي حقيقي: نوقف التشغيل الحالي ونبدأ التالي
    await call_py.leave_group_call(chat_id)
    # ننتظر قليلاً حتى يتم تنظيف المكالمة ثم نشغل التالي
    await asyncio.sleep(1)
    await play_next(chat_id)

@bot.on_message(filters.command("ايقاف") & filters.group)
@admin_required
async def stop_command(client, message: Message):
    chat_id = message.chat.id
    await call_py.leave_group_call(chat_id)
    current_song.pop(chat_id, None)
    if chat_id in queues:
        q = queues[chat_id]
        while not q.empty():
            await q.get()
        del queues[chat_id]
    clear_queue_sync(chat_id)
    clear_playback_state(chat_id)
    song_ended_flags.pop(chat_id, None)
    await message.reply_text("⏹️ تم الإيقاف الكامل ومسح الكيو.")

@bot.on_message(filters.command("كتم") & filters.group)
@admin_required
async def mute_command(client, message: Message):
    try:
        await call_py.change_volume_call(message.chat.id, 0)
        await message.reply_text("🔇 تم الكتم.")
    except Exception:
        await message.reply_text("المساعد غير متصل بالمكالمة.")

@bot.on_message(filters.command("تحدث") & filters.group)
@admin_required
async def unmute_command(client, message: Message):
    try:
        await call_py.change_volume_call(message.chat.id, 100)
        await message.reply_text("🔊 تم إلغاء الكتم.")
    except Exception:
        await message.reply_text("المساعد غير متصل بالمكالمة.")

@bot.on_message(filters.command("كيو") & filters.group)
async def queue_command(client, message: Message):
    if not await check_force_sub(client, message.from_user.id):
        channel, _ = get_force_sub()
        return await force_sub_message(message.chat.id, channel)
    chat_id = message.chat.id
    q = await get_queue(chat_id)
    if not q.empty():
        items = []
        temp_q = asyncio.Queue()
        while not q.empty():
            item = await q.get()
            items.append(item)
            await temp_q.put(item)
        while not temp_q.empty():
            await q.put(await temp_q.get())
        qlist = "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])
        await message.reply_text(f"📜 قائمة الانتظار:\n{qlist}")
    else:
        await message.reply_text("الكيو فارغة.")

@bot.on_message(filters.command("احذف") & filters.group)
@admin_required
async def remove_from_queue(client, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        return await message.reply_text("استخدم: /احذف رقم_الأغنية")
    try:
        index = int(message.command[1]) - 1
        q = await get_queue(chat_id)
        if q.empty():
            return await message.reply_text("الكيو فارغة.")
        items = []
        while not q.empty():
            items.append(await q.get())
        if 0 <= index < len(items):
            removed = items.pop(index)
            for item in items:
                await q.put(item)
            save_queue_sync(chat_id, items)
            await message.reply_text(f"🗑️ تم حذف: {removed}")
        else:
            await message.reply_text("رقم غير صحيح.")
            for item in items:
                await q.put(item)
    except Exception:
        await message.reply_text("حدث خطأ.")

@bot.on_message(filters.command("مسح_الكيو") & filters.group)
@admin_required
async def clear_queue_cmd(client, message: Message):
    chat_id = message.chat.id
    q = await get_queue(chat_id)
    while not q.empty():
        await q.get()
    clear_queue_sync(chat_id)
    await message.reply_text("🧹 تم مسح الكيو بالكامل.")

@bot.on_message(filters.command("بنك"))
async def ping_command(client, message: Message):
    start = time.time()
    msg = await message.reply_text("⚡")
    await msg.edit(f"🚀 `{round((time.time()-start)*1000)} ms`")

# ================== الإذاعة ==================
async def broadcast_worker():
    while True:
        chat_id, text = await broadcast_queue.get()
        try:
            await bot.send_message(chat_id, text)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await bot.send_message(chat_id, text)
            except Exception:
                pass
        except Exception:
            pass
        broadcast_queue.task_done()

@bot.on_message(filters.command("اذاعة") & filters.user(config.OWNER_ID))
async def broadcast_owner(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("اكتب الرسالة للإذاعة. مثال: /اذاعة مرحبا")
    text = message.text.split(None, 1)[1]
    chats = list(ACTIVATED_CHATS)
    if not chats:
        return await message.reply_text("لا توجد مجموعات نشطة.")
    for chat_id in chats:
        await broadcast_queue.put((chat_id, text))
    await message.reply_text(f"✅ تمت جدولة الإذاعة إلى {len(chats)} مجموعة. ستُرسل تباعاً.")

# ================== الأزرار ==================
@bot.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "add_sudo" and user_id == config.OWNER_ID:
        await query.answer("أرسل /اضف + ايدي", show_alert=True)
    elif data == "del_sudo" and user_id == config.OWNER_ID:
        await query.answer("أرسل /حذف + ايدي", show_alert=True)
    elif data == "sudo_list":
        txt = "👥 المطورين:\n" + "\n".join([f"`{u}`" for u in SUDO_USERS]) if SUDO_USERS else "لا يوجد."
        await query.answer(txt, show_alert=True)
    elif data == "user_help":
        await query.message.edit_text(
            "**الأوامر للمشرفين:**\n"
            "/شغل - /تخطي - /ايقاف - /كتم - /تحدث\n"
            "/كيو - /احذف رقم - /مسح_الكيو\n"
            "/بنك",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ رجوع", callback_data="back_start")]])
        )
    elif data == "set_name" and user_id == config.OWNER_ID:
        await query.answer("أرسل /تعيين + الاسم الجديد", show_alert=True)
    elif data == "bot_info":
        info = f"📊 المجموعات النشطة: {len(ACTIVATED_CHATS)}\n👥 المطورين: {len(SUDO_USERS)}"
        channel, enabled = get_force_sub()
        if enabled:
            info += f"\n🔐 الاشتراك الإجباري: مفعل في {channel}"
        else:
            info += "\n🔓 الاشتراك الإجباري: معطل"
        await query.answer(info, show_alert=True)
    elif data == "restart_bot" and user_id == config.OWNER_ID:
        await query.message.reply_text("🔄 جارٍ إعادة التشغيل...")
        await asyncio.sleep(1)
        os.execv(sys.executable, ['python'] + sys.argv)
    elif data == "broadcast_owner" and user_id == config.OWNER_ID:
        await query.answer("أرسل /اذاعة + الرسالة", show_alert=True)
    elif data == "dev_stats":
        info = f"📊 المجموعات النشطة: {len(ACTIVATED_CHATS)}"
        await query.answer(info, show_alert=True)
    elif data == "dev_broadcast":
        await query.answer("خاصية الإذاعة قيد التطوير للمطورين", show_alert=True)
    elif data == "back_start":
        await send_start_interface(query.message, user_id)
    elif data == "set_force_on" and user_id == config.OWNER_ID:
        await query.answer("أرسل /تفعيل_اشتراك + @معرف_القناة", show_alert=True)
    elif data == "set_force_off" and user_id == config.OWNER_ID:
        set_force_sub("", 0)
        await query.answer("تم تعطيل الاشتراك الإجباري", show_alert=True)
    elif data == "check_sub":
        if await check_force_sub(client, user_id):
            await query.answer("✅ أنت مشترك، يمكنك استخدام البوت الآن", show_alert=True)
            try:
                await query.message.delete()
            except Exception:
                pass
        else:
            channel, _ = get_force_sub()
            await query.answer("❌ لم تشترك بعد!", show_alert=True)
            await force_sub_message(query.message.chat.id, channel)

# ================== أوامر المالك ==================
@bot.on_message(filters.command("اضف") & filters.user(config.OWNER_ID))
async def add_sudo_cmd(client, message: Message):
    try:
        uid = int(message.command[1])
        SUDO_USERS.add(uid)
        save_sudo(uid)
        await message.reply_text(f"✅ تم رفع `{uid}` كمطور.")
    except (IndexError, ValueError):
        await message.reply_text("استخدم: /اضف ايدي")

@bot.on_message(filters.command("حذف") & filters.user(config.OWNER_ID))
async def del_sudo_cmd(client, message: Message):
    try:
        uid = int(message.command[1])
        SUDO_USERS.discard(uid)
        remove_sudo_db(uid)
        await message.reply_text(f"❌ تم حذف `{uid}`.")
    except (IndexError, ValueError):
        await message.reply_text("استخدم: /حذف ايدي")

@bot.on_message(filters.command("تعيين") & filters.user(config.OWNER_ID))
async def set_name_cmd(client, message: Message):
    global bot_name
    if len(message.command) < 2:
        return await message.reply_text("اكتب الاسم الجديد. مثال: /تعيين ميوزك بوت")
    new_name = message.text.split(None, 1)[1]
    bot_name = new_name
    set_bot_name_db(new_name)
    await message.reply_text(f"✅ تم تعيين اسم البوت إلى: {bot_name}")

@bot.on_message(filters.command("تفعيل_اشتراك") & filters.user(config.OWNER_ID))
async def enable_force_sub_cmd(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("استخدم: /تفعيل_اشتراك @معرف_القناة")
    channel = message.command[1]
    if not channel.startswith("@"):
        channel = "@" + channel
    set_force_sub(channel, 1)
    await message.reply_text(f"✅ تم تفعيل الاشتراك الإجباري في {channel}")

@bot.on_message(filters.command("تعطيل_اشتراك") & filters.user(config.OWNER_ID))
async def disable_force_sub_cmd(client, message: Message):
    set_force_sub("", 0)
    await message.reply_text("✅ تم تعطيل الاشتراك الإجباري.")

# ================== مهام الخلفية ==================
async def cleanup_old_files():
    while True:
        await asyncio.sleep(1800)
        now = time.time()
        try:
            for f in os.listdir(DOWNLOADS_DIR):
                filepath = os.path.join(DOWNLOADS_DIR, f)
                if os.path.isfile(filepath) and (now - os.path.getmtime(filepath)) > 1800:
                    os.remove(filepath)
                    logger.info(f"Deleted old file: {filepath}")
        except FileNotFoundError:
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def health_check():
    while True:
        await asyncio.sleep(300)
        try:
            await bot.get_me()
            logger.info("Health check: Bot OK")
        except Exception:
            logger.error("Health check: Bot unresponsive")

async def restore_playback():
    states = load_all_playback_states()
    for chat_id, title, file_path in states:
        if file_path and os.path.exists(file_path):
            try:
                await call_py.join_group_call(chat_id, AudioPiped(file_path))
                current_song[chat_id] = {"title": title, "file": file_path}
                ACTIVATED_CHATS.add(chat_id)
                logger.info(f"Restored playback in {chat_id}: {title}")
            except Exception:
                clear_playback_state(chat_id)  # فشل، حذف الحالة

# ================== Main ==================
async def main():
    global broadcast_worker_task
    await bot.start()
    await assistant.start()
    await call_py.start()
    await get_bot_username()
    logger.info(f"{bot_name} started successfully!")

    # استعادة التشغيل السابق
    await restore_playback()

    # تشغيل broadcast worker مرة واحدة
    if broadcast_worker_task is None:
        broadcast_worker_task = asyncio.create_task(broadcast_worker())

    # مهام الخلفية
    asyncio.create_task(cleanup_old_files())
    asyncio.create_task(health_check())

    # استخدام idle من pytgcalls لضمان معالجة الأحداث بشكل صحيح
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
