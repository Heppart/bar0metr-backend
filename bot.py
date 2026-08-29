import os
import requests
from telegram import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

def start(update, context):
    user = update.effective_user
    tg_id = str(user.id)
    try:
        requests.post(f"{API_URL}/register", json={
            "tg_id": tg_id,
            "first_name": user.first_name,
            "username": user.username,
            "is_premium": getattr(user, 'is_premium', False)
        })
    except:
        pass
    contact_btn = KeyboardButton("📱 Поделиться номером", request_contact=True)
    webapp_btn = KeyboardButton("🌍 Открыть карту", web_app=WebAppInfo(url="https://bar0metr.ru/index.html"))
    reply_markup = ReplyKeyboardMarkup([[contact_btn, webapp_btn]], resize_keyboard=True)
    update.message.reply_text(
        "👋 Добро пожаловать в Бар0метр!\n\n"
        "📍 Карта живых людей в заведениях города.\n"
        "1️⃣ Поделись номером — чтобы отмечаться\n"
        "2️⃣ Открой карту — смотри, где есть компания",
        reply_markup=reply_markup
    )

def contact_handler(update, context):
    contact = update.message.contact
    if contact:
        update.message.reply_text("✅ Номер получен! Теперь вы можете отмечаться в заведениях.")

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()