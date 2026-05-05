import os
import asyncio
import logging
import random
import json
import openai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, BotCommand, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()
ai_client = openai.OpenAI(api_key=OPENAI_KEY)

# Константы
GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"
purchase_attempts = 0

# --- МЕНЮ КОМАНД ---
async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Главное меню 🚀"),
        BotCommand(command="/find_us", description="Где наш стенд? 📍"),
        BotCommand(command="/buy", description="Купить катушку 🛒"),
        BotCommand(command="/vcard", description="Контакт DRUKAR 📇"),
    ]
    await bot.set_my_commands(commands)

# --- ГЛАВНАЯ КЛАВИАТУРА ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея работ", callback_data="gallery"))
    builder.row(InlineKeyboardButton(text="📇 Сохранить контакт DRUKAR", callback_data="get_vcard"))
    builder.row(InlineKeyboardButton(text="📸 Отправить визитку", callback_data="scan_card"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Приветствуем на стенде **DRUKAR**! 🚀\n\n"
        "Мы — украинский производитель материалов для 3D-печати. "
        "Специализируемся на оптовых поставках и качестве для профи.\n\n"
        "📸 **Пришлите фото визитки**, и я мгновенно сохраню ваши данные!",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

# 1. ПРОФЕССИОНАЛЬНОЕ РАСПОЗНАВАНИЕ ВИЗИТОК
@dp.callback_query(F.data == "scan_card")
async def ask_for_card(callback: types.CallbackQuery):
    await callback.message.answer("📸 Пришлите фото визитки. Я распознаю всё: от телефонов до соцсетей и описания!")
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not OPENAI_KEY:
        return await message.answer("⚠️ Ошибка: API ключ OpenAI не настроен.")

    status_msg = await message.answer("🔍 Интеллектуальное сканирование визитки... Подождите.")
    
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    prompt = (
        "Проанализируй фото визитки. Твоя цель — извлечь ВСЕ данные. "
        "Обязательно найди: сайты (даже сложные), соцсети (Instagram, Telegram ники, FB), "
        "адреса и описание деятельности компании. "
        "Верни JSON: {name, company, position, phones[], emails[], website, social, address, description}. "
        "Если данных нет, ставь ''. Используй кириллицу."
    )

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": file_url}}]}],
            response_format={ "type": "json_object" }
        )
        
        data = json.loads(response.choices[0].message.content)
        
        # Красивый вывод пользователю
        res = "✅ **Данные визитки получены:**\n\n"
        if data.get("name"): res += f"👤 **Имя:** {data['name']}\n"
        if data.get("company"): res += f"🏢 **Компания:** {data['company']}\n"
        if data.get("description"): res += f"📝 **О чем:** {data['description']}\n"
        if data.get("phones"): res += f"📞 **Тел:** {', '.join(data['phones']) if isinstance(data['phones'], list) else data['phones']}\n"
        if data.get("emails"): res += f"📧 **Email:** {', '.join(data['emails']) if isinstance(data['emails'], list) else data['emails']}\n"
        if data.get("website"): res += f"🌐 **Сайт:** {data['website']}\n"
        if data.get("social"): res += f"📱 **Соцсети/Мессенджеры:** {data['social']}\n"
        if data.get("address"): res += f"📍 **Адрес:** {data['address']}\n"

        await status_msg.edit_text(res, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await status_msg.edit_text("❌ Не удалось распознать фото. Попробуйте сделать его более четким.")

# 2. КОРПОРАТИВНЫЙ КОНТАКТ DRUKAR (vCard)
@dp.message(Command("vcard"))
@dp.callback_query(F.data == "get_vcard")
async def send_vcard(event):
    message = event if isinstance(event, types.Message) else event.message
    
    vcard_data = (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:DRUKAR | 3D Printing Materials\n"
        "ORG:DRUKAR\n"
        "TITLE:Производитель филамента\n"
        "TEL;TYPE=WORK,VOICE:+380XXXXXXXXX\n" # Укажи реальный номер
        "EMAIL:info@3drukar.com\n"
        "URL:https://www.3drukar.com\n"
        "NOTE:Стенд A-45 на Addit EXPO 3D-2026\n"
        "END:VCARD"
    )
    
    await message.answer_contact(
        phone_number="+380XXXXXXXXX", # Укажи реальный номер
        first_name="DRUKAR",
        last_name="3D Materials",
        vcard=vcard_data
    )
    await message.answer("👆 Нажмите на контакт выше, чтобы сохранить нас в адресную книгу!")
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

# 3. ПОКУПКА С СОЦИАЛЬНЫМ ДОКАЗАТЕЛЬСТВОМ
@dp.message(Command("buy"))
@dp.callback_query(F.data == "buy_filament")
async def cmd_buy(event):
    global purchase_attempts
    message = event if isinstance(event, types.Message) else event.message
    purchase_attempts += random.randint(1, 3)
    display_count = 142 + purchase_attempts

    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}qr_payment.png",
        caption=(
            f"🔥 **Хит продаж!**\n"
            f"Сегодня этот товар заказали уже **{display_count}** раз.\n\n"
            f"🛒 **Оплата на ФОП**\n"
            f"Отсканируйте код и отправьте квитанцию в этот чат.\n\n"
            f"Выдача на стенде A-45. Спасибо за доверие!"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

# 4. ГДЕ НАШ СТЕНД
@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}event_preview.jpg",
        caption=(
            "📍 **DRUKAR на Addit EXPO 3D-2026**[cite: 1]\n\n"
            "🏢 Киев, МВЦ (Броварской пр-т, 15)[cite: 1]\n"
            "✅ Стенд: **A-45 (Павильон №2)**\n\n"
            "🔗 [Сайт выставки](https://www.iec-expo.com.ua/addit-2026.html)"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

# 5. ГАЛЕРЕЯ
@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Загружаю галерею наших работ...")
    album = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    try:
        await callback.message.answer_media_group(media=album)
    except Exception:
        await callback.message.answer("⚠️ Фотографии в пути, попробуйте снова.")
    await callback.answer()

# --- СТАРТ ---
async def main():
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("DRUKAR Bot Live!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())