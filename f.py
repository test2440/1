# -*- coding: utf-8 -*-

import telebot
import os
import zipfile
import tempfile
import logging

# إعداد التوكن الخاص بالبوت
TOKEN = '6383532072:AAGkOq2B-0gcVwwv8OI6l_N2v13SsaxqqD0'
bot = telebot.TeleBot(TOKEN)

# إعداد تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)

def zip_directory(directory_path, temp_dir):
    zip_path = os.path.join(temp_dir, f"{os.path.basename(directory_path)}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=directory_path)
                try:
                    zipf.write(file_path, arcname=arcname)
                except FileNotFoundError:
                    logging.warning(f"File not found: {file_path}")
                except Exception as e:
                    logging.error(f"Error adding file {file_path}: {e}")
    return zip_path

# التعامل مع رسالة الأمر /compress
@bot.message_handler(commands=['compress'])
def compress_and_send(message):
    with tempfile.TemporaryDirectory() as temp_dir:
        for item in os.listdir():
            if os.path.isfile(item):
                try:
                    zip_path = os.path.join(temp_dir, f"{item}.zip")
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(item, arcname=item)
                    with open(zip_path, 'rb') as zip_file:
                        bot.send_document(message.chat.id, zip_file, caption=f"{item}.zip")
                except Exception as e:
                    logging.error(f"Error processing file {item}: {e}")
            elif os.path.isdir(item):
                try:
                    zip_path = zip_directory(item, temp_dir)
                    with open(zip_path, 'rb') as zip_file:
                        bot.send_document(message.chat.id, zip_file, caption=f"{item}.zip")
                except Exception as e:
                    logging.error(f"Error processing directory {item}: {e}")

# تشغيل البوت
bot.polling()

