# 🎵 بوت موسيقى تيليجرام | Telegram Music Bot v6

<p align="center">
  <b>سورس احترافي متكامل لبث وتشغيل الصوتيات داخل مكالمات تيليجرام</b>
</p>

<p align="center">
  <a href="https://github.com/saifali2580/telegram-music-bot/stargazers"><img src="https://img.shields.io/github/stars/saifali2580/telegram-music-bot?style=for-the-badge&color=yellow" alt="Stars"></a>
  <a href="https://github.com/saifali2580/telegram-music-bot/network/members"><img src="https://img.shields.io/github/forks/saifali2580/telegram-music-bot?style=for-the-badge&color=blue" alt="Forks"></a>
  <a href="https://github.com/saifali2580/telegram-music-bot/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python" alt="Python"></a>
</p>

---

# ✨ المميزات

- 🎧 تشغيل صوتي عالي الجودة بدون تقطيع
- 🔍 بحث متعدد المنصات: YouTube • SoundCloud • Spotify
- 📜 نظام Queue احترافي مع حفظ دائم في قاعدة البيانات
- ⏭️ تخطي حقيقي مع تشغيل تلقائي للأغنية التالية
- 🔐 نظام اشتراك إجباري مع أزرار تحقق انلاين
- 👑 لوحة تحكم كاملة للمالك والمطورين بأزرار شفافة
- 📢 نظام إذاعة متقدم مع حماية من FloodWait
- 🔄 استعادة تلقائية للتشغيل بعد إعادة التشغيل
- 🗑️ تنظيف تلقائي للملفات المؤقتة
- 🛡️ حماية من السبام مع تحديد وقت بين الأوامر
- 📊 نظام سجلات (Logging) لمراقبة الأداء
- 🤖 حساب مساعد ذكي للانضمام للمكالمات الصوتية
- 💾 قاعدة بيانات SQLite لحفظ جميع البيانات

---

# 🛠️ جميع الأوامر

## 🎵 أوامر التشغيل (للمشرفين)

| الأمر | الوظيفة |
|--------|---------|
| `شغل` أو `play` + اسم الأغنية | البحث في يوتيوب والتشغيل مباشرة |
| `تخطي` أو `skip` | تخطي الأغنية الحالية وتشغيل التالية |
| `ايقاف` أو `stop` | إيقاف التشغيل ومسح قائمة الانتظار |
| `كتم` أو `mute` | كتم صوت المساعد داخل المكالمة |
| `تحدث` أو `unmute` | إلغاء الكتم وإعادة الصوت |

---

## 📜 أوامر قائمة الانتظار

| الأمر | الوظيفة |
|--------|---------|
| `كيو` أو `queue` | عرض قائمة الانتظار الحالية |
| `احذف` + رقم الأغنية | حذف أغنية محددة من القائمة |
| `مسح_الكيو` أو `clear` | مسح قائمة الانتظار بالكامل |

---

## ⚡ أوامر عامة

| الأمر | الوظيفة |
|--------|---------|
| `بنك` أو `ping` | فحص سرعة استجابة السيرفر |
| `/start` | عرض واجهة البوت الرئيسية |

---

## 👑 أوامر المالك (خاصة)

| الأمر | الوظيفة |
|--------|---------|
| `اضف` + ايدي | رفع مطور جديد للبوت |
| `حذف` + ايدي | تنزيل مطور من البوت |
| `تعيين` + اسم | تغيير اسم البوت |
| `تفعيل_اشتراك` + @معرف_القناة | تفعيل الاشتراك الإجباري |
| `تعطيل_اشتراك` | تعطيل الاشتراك الإجباري |
| `اذاعة` + رسالة | إرسال إذاعة لجميع المجموعات النشطة |

---

# 📋 المتطلبات

| المتطلب | الإصدار |
|----------|----------|
| Python | 3.9 أو أحدث |
| Pyrogram | 2.0.106 أو أحدث |
| PyTgCalls | 3.0.0.dev25 أو أحدث |
| yt-dlp | 2024.08.06 أو أحدث |
| FFmpeg | أي إصدار حديث |

---

# ⚙️ إعداد البوت بالكامل

## 1️⃣ إنشاء بوت من BotFather

1. افتح @BotFather
2. أرسل:
```text
/newbot
```
3. اختر اسم للبوت
4. اختر يوزر ينتهي بـ `bot`
5. انسخ `BOT_TOKEN`

---

## 2️⃣ الحصول على API_ID و API_HASH

اذهب إلى:

🔗 https://my.telegram.org

ثم:

1. سجل دخول برقمك
2. ادخل إلى:
```text
API Development Tools
```
3. أنشئ تطبيق جديد
4. انسخ:
- API_ID
- API_HASH

---

## 3️⃣ إنشاء STRING_SESSION

يمكنك إنشاء جلسة الحساب المساعد عبر:

- سكريبت Pyrogram
- بوتات توليد الجلسات
- Replit أو Termux أو VPS

بعد إنشاء الجلسة انسخ:
```text
STRING_SESSION
```

---

## 4️⃣ إنشاء ملف config.env

أنشئ ملف باسم:

```text
config.env
```

ثم ضع بداخله:

```env
API_ID=123456
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
STRING_SESSION=your_string_session
OWNER_ID=123456789
```

---

# ☁️ النشر المباشر

## 🚀 النشر على Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

### خطوات النشر:

1. اضغط Deploy
2. سجل دخول بحساب GitHub
3. أضف المتغيرات التالية:

| المتغير | الوصف |
|----------|--------|
| API_ID | من my.telegram.org |
| API_HASH | من my.telegram.org |
| BOT_TOKEN | من BotFather |
| STRING_SESSION | جلسة الحساب المساعد |
| OWNER_ID | ايديك الرقمي |

4. انتظر حتى يكتمل النشر
5. شغل البوت 🚀

---

## 🐳 النشر باستخدام Docker

```bash
docker build -t music-bot .

docker run -d \
  --name music-bot \
  -e API_ID=123456 \
  -e API_HASH="your_api_hash" \
  -e BOT_TOKEN="your_bot_token" \
  -e STRING_SESSION="your_session" \
  -e OWNER_ID=123456789 \
  --restart always \
  music-bot
```

---

# 🖥️ التنصيب على VPS

## 📦 تثبيت تلقائي بسطر واحد

```bash
git clone https://github.com/saifali2580/telegram-music-bot.git && cd telegram-music-bot && chmod +x setup.sh && sudo bash setup.sh
```

---

## 🔧 ماذا يفعل setup.sh ؟

- تحديث السيرفر بالكامل
- تثبيت Python و FFmpeg
- تثبيت المكتبات المطلوبة
- إنشاء ملف config.env
- إنشاء خدمة systemd
- تشغيل البوت تلقائياً 24/7
- إعادة تشغيل تلقائية عند التوقف

---

## ▶️ تشغيل البوت يدوياً

```bash
python3 main.py
```

---

## 🔄 تشغيل البوت بالخلفية

```bash
screen -S musicbot
python3 main.py
```

للخروج بدون إيقاف البوت:

```bash
CTRL + A ثم D
```

---

## 📌 أوامر إدارة الخدمة

### تشغيل البوت

```bash
sudo systemctl start musicbot
```

### إيقاف البوت

```bash
sudo systemctl stop musicbot
```

### إعادة تشغيل البوت

```bash
sudo systemctl restart musicbot
```

### معرفة حالة البوت

```bash
sudo systemctl status musicbot
```

### مشاهدة السجلات

```bash
journalctl -u musicbot -f
```

---

# 📁 هيكل المشروع

```text
telegram-music-bot/
├── main.py
├── config.py
├── config.env.example
├── requirements.txt
├── Dockerfile
├── Procfile
├── setup.sh
├── README.md
├── music_bot.db
└── downloads/
```

---

# ❓ الأسئلة الشائعة

<details>
<summary><b>البوت لا يشغل الأغاني؟</b></summary>

تأكد من:

- تثبيت FFmpeg
- الحساب المساعد داخل المجموعة
- رفع البوت والمساعد مشرفين
- وجود صلاحية التحدث بالمكالمة

</details>

---

<details>
<summary><b>كيف أضيف البوت لمجموعتي؟</b></summary>

1. افتح البوت
2. اضغط إضافة إلى مجموعة
3. اختر المجموعة
4. أضف الحساب المساعد أيضاً
5. ارفعهم مشرفين

</details>

---

<details>
<summary><b>كيف أغير اسم البوت أو صورته؟</b></summary>

من @BotFather استخدم:

```text
/setname
/setuserpic
```

</details>

---

# 👨‍💻 للمطورين

```bash
git clone https://github.com/saifali2580/telegram-music-bot.git

cd telegram-music-bot

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

cp config.env.example config.env

nano config.env

source config.env && python3 main.py
```

---

# 📱 تواصل معنا

<p align="center">
  <a href="https://t.me/DowzC"><img src="https://img.shields.io/badge/Telegram-%40DowzC-blue?style=for-the-badge&logo=telegram"></a>
  <a href="https://t.me/wofkq"><img src="https://img.shields.io/badge/Channel-Dowz%20Source-red?style=for-the-badge&logo=telegram"></a>
  <a href="https://www.tiktok.com/@qq_db"><img src="https://img.shields.io/badge/TikTok-%40qq__db-black?style=for-the-badge&logo=tiktok"></a>
  <a href="https://www.instagram.com/qq_db"><img src="https://img.shields.io/badge/Instagram-%40qq__db-E4405F?style=for-the-badge&logo=instagram"></a>
  <a href="https://github.com/saifali2580"><img src="https://img.shields.io/badge/GitHub-saifali2580-black?style=for-the-badge&logo=github"></a>
</p>

---

# 📄 الترخيص

هذا المشروع مرخص تحت MIT License.

---

<p align="center">
  <b>صنع بـ ❤️ بواسطة <a href="https://t.me/DowzC">سيف - DowzC</a></b>
</p>
