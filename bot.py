import os
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(
        "👋 Добро пожаловать в Бар0метр!\n\n"
        "📍 Карта живых людей в заведениях города.\n"
        "1️⃣ Поделись номером — чтобы отмечаться\n"
        "2️⃣ Открой карту — смотри, где есть компания",
        reply_markup=reply_markup
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if contact:
        await update.message.reply_text("✅ Номер получен! Теперь вы можете отмечаться в заведениях.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.run_polling()

if __name__ == "__main__":
    main()