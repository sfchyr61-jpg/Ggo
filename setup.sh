#!/bin/bash

set -e

echo "======================================"
echo "  🎧 تنصيب بوت الميوزك v6"
echo "======================================"
echo ""

# تأكد من صلاحيات root
if [ "$EUID" -ne 0 ]; then
  echo "يرجى تشغيل السكريبت بصلاحيات root (sudo)"
  exit 1
fi

# جمع المعلومات من المستخدم
read -p "أدخل API_ID: " API_ID
read -p "أدخل API_HASH: " API_HASH
read -p "أدخل BOT_TOKEN: " BOT_TOKEN
read -p "أدخل STRING_SESSION: " STRING_SESSION
read -p "أدخل OWNER_ID: " OWNER_ID

# تحديث النظام وتثبيت الحزم
echo ""
echo "🔄 تحديث النظام وتثبيت الحزم..."
apt update -qq && apt install -y -qq python3 python3-pip python3-venv git ffmpeg

# إعداد المجلد
APP_DIR="/root/music-bot"
if [ -d "$APP_DIR" ]; then
  echo "المجلد موجود، جاري تحديث الملفات..."
  cd "$APP_DIR"
  git pull
else
  echo "📥 تحميل المشروع من GitHub..."
  read -p "أدخل رابط مستودع GitHub: " REPO_URL
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

# إنشاء ملف config.env
cat > config.env <<EOF
API_ID=$API_ID
API_HASH=$API_HASH
BOT_TOKEN=$BOT_TOKEN
STRING_SESSION=$STRING_SESSION
OWNER_ID=$OWNER_ID
EOF

# إعداد البيئة الافتراضية
echo "🐍 إعداد البيئة الافتراضية..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# إنشاء خدمة systemd
echo "⚙️  إنشاء خدمة systemd..."
cat > /etc/systemd/system/music-bot.service <<EOF
[Unit]
Description=Telegram Music Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/config.env
ExecStart=$APP_DIR/venv/bin/python3 $APP_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/bot.log
StandardError=append:$APP_DIR/bot.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable music-bot
systemctl start music-bot

echo ""
echo "✅ تم التنصيب والتشغيل!"
echo "🔍 حالة البوت: systemctl status music-bot"
echo "📋 متابعة السجلات: journalctl -u music-bot -f"
