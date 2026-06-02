FROM python:3.10-slim

# تثبيت ffmpeg (ضروري لتشغيل الصوت)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# تشغيل البوت الرئيسي (تأكد من اسم الملف main.py)
CMD ["python3", "main.py"]
