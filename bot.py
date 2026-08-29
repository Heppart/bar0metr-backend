from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json

TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
API_URL = "https://ВАШ-БЭКЕНД.onrender.com"  # URL бэкенда на Render

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = str(user.id)
    
    # Кнопка для запроса телефона
    contact_btn = KeyboardButton("📱 Поделиться номером", request_contact=True)
    # Кнопка для открытия карты (WebApp)
    webapp_btn = KeyboardButton("🌍 Открыть карту", web_app=WebAppInfo(url="https://ВАШ-САЙТ.ru"))
    
    reply_markup = ReplyKeyboardMarkup(
        [[contact_btn, webapp_btn]],
        resize_keyboard=True
    )
    
    await update.message.reply_text(
        "👋 Добро пожаловать в Бар0метр!\n\n"
        "📍 Карта живых людей в заведениях города.\n"
        "1️⃣ Поделись номером — чтобы отмечаться\n"
        "2️⃣ Открой карту — смотри, где есть компания",
        reply_markup=reply_markup
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("❌ Пожалуйста, поделись номером через кнопку.")
        return
    
    tg_id = str(update.effective_user.id)
    phone = contact.phone_number
    
    response = requests.post(f"{API_URL}/register", json={
        "tg_id": tg_id,
        "phone": phone
    })
    
    if response.status_code == 200:
        await update.message.reply_text(
            "✅ Отлично! Теперь ты можешь отмечаться в заведениях.\n\n"
            "Нажми «Открыть карту» и выбери место."
        )
    else:
        await update.message.reply_text("❌ Ошибка сервера, попробуй позже.")

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка геолокации от пользователя"""
    location = update.message.location
    tg_id = str(update.effective_user.id)
    
    # Здесь можно добавить логику: если пользователь прислал гео — показать ближайшие заведения
    # Пока просто отвечаем
    await update.message.reply_text(
        f"📍 Координаты получены: {location.latitude}, {location.longitude}\n"
        "Открой карту, чтобы увидеть заведения рядом."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Как пользоваться Бар0метром:\n\n"
        "1. Поделись номером телефона\n"
        "2. Открой карту и выбери заведение\n"
        "3. Нажми «Я здесь», когда придёшь\n"
        "4. Нажми «Мне ок», чтобы показать, что готов к общению\n"
        "5. Если кто-то ещё нажал «Ок» — вы увидите друг друга!"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    
    print("🤖 Бот запущен и работает...")
    app.run_polling()

if __name__ == "__main__":
    main()