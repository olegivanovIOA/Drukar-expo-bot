import os
import asyncio
import logging
import random
import openai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, BotCommand, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Инициализация клиентов
bot = Bot(token=TOKEN)
dp = Dispatcher()
ai_client = openai.OpenAI(api_key=OPENAI_KEY)

# Путь к вашим медиа-файлам на GitHub
GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

# Глобальный счетчик (для Social Proof)
purchase_attempts = 0

# --- НАСТРОЙКА МЕНЮ ---
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Главное меню 🚀"),
        BotCommand(command="/find_us", description="Где наш стенд? 📍"),
        BotCommand(command="/buy", description="Купить катушку 🛒"),
        BotCommand(command="/vcard", description="Мой контакт 📇"),
    ]
    await bot.set_my_commands(main_menu_commands)

# --- ИНЛАЙН КЛАВИАТУРА ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея работ", callback_data="gallery"))
    builder.row(InlineKeyboardButton(text="📇 Сохранить мой контакт", callback_data="get_vcard"))
    builder.row(InlineKeyboardButton(text="📝 Отправить визитку (фото)", callback_data="scan_card"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Приветствуем на стенде **Drukar**! 🚀\n\n"
        f"Мы — украинский производитель филамента для 3D-печати.\n"
        f"Пришлите мне фото вашей визитки, и я сохраню ваши данные, либо воспользуйтесь меню ниже.",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

# 1. РАСПОЗНАВАНИЕ ВИЗИТКИ
@dp.callback_query(F.data == "scan_card")
async def ask_for_card(callback: types.CallbackQuery):
    await callback.message.answer("📸 Просто пришлите мне фото вашей визитки одним сообщением!")
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not OPENAI_KEY:
        return await message.answer("⚠️ Модуль ИИ не настроен (проверьте API ключ).")

    msg = await message.answer("🔍 Распознаю данные с визитки через ИИ...")
    
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract: name, company, position, phone, email. Return JSON only."},
                        {"type": "image_url", "image_url": {"url": file_url}}
                    ],
                }
            ],
            response_format={ "type": "json_object" }
        )
        data = response.choices[0].message.content
        await msg.edit_text(f"✅ Данные визитки получены:\n\n`{data}`\n\nМенеджер свяжется с вами!", parse_mode="Markdown")
        # Тут можно добавить код отправки в CRM
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await msg.edit_text("❌ Не удалось распознать. Попробуйте сделать фото четче.")

# 2. VCARD (ПОДЕЛИТЬСЯ СВОИМ КОНТАКТОМ)
@dp.message(Command("vcard"))
@dp.callback_query(F.data == "get_vcard")
async def send_vcard(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer_contact(
        phone_number="+380XXXXXXXXX", # Замени на свой
        first_name="Oleg",
        last_name="Ivanov",
        vcard="BEGIN:VCARD\nVERSION:3.0\nFN:Oleg Ivanov\nORG:DRUKAR\nTITLE:CEO\nTEL:+380XXXXXXXXX\nURL:https://3drukar.com\nEND:VCARD"
    )
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
            f"🔥 **Популярный выбор!**\nЭту катушку сегодня выбрали уже **{display_count}** раз.\n\n"
            f"🛒 **Оплата ФОП**\nОтсканируйте QR и пришлите квитанцию в чат.\n\n"
            f"Забрать можно на стенде A-45![cite: 1]"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

# 4. ГДЕ МЫ (ВЫСТАВКА)
@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}event_preview.jpg",
        caption=(
            "📍 **DRUKAR на Addit EXPO 3D-2026**[cite: 1]\n\n"
            "🏢 Киев, МВЦ, Павильон №2, стенд A-45[cite: 1]\n"
            "🔗 [Подробности выставки](https://www.iec-expo.com.ua/addit-2026.html)"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

# 5. ГАЛЕРЕЯ
@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Загружаю галерею Drukar...")
    album = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    try:
        await callback.message.answer_media_group(media=album)
    except Exception:
        await callback.message.answer("⚠️ Фото подгружаются, попробуйте снова через секунду.")
    await callback.answer()

# --- ЗАПУСК ---
async def main():
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот Drukar запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())