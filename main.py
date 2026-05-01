import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Путь к вашим медиа-файлам на GitHub
GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

def get_main_menu():
    builder = InlineKeyboardBuilder()
    
    # Ссылки на внешние ресурсы
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", url="https://calendly.com/ioa4/30min"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", url="https://www.3drukar.com/shop"))
    
    # Кнопки с внутренней логикой
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="💎 Галерея работ", callback_data="gallery"))
    
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Приветствуем на стенде **Drukar**! 🚀\n\n"
        f"Мы производим высококачественные инженерные филаменты для 3D-печати.\n"
        f"Чем я могу вам помочь?",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "find_us")
async def find_us(callback: types.CallbackQuery):
    # Отправка фото карты (убедитесь, что map.jpg есть в репозитории)
    photo_url = GITHUB_BASE_URL + "map.jpg"
    await callback.message.answer_photo(
        photo=photo_url,
        caption="📍 **Мы в Павильоне №2, стенд A-45.**\nЖдем вас!",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Загружаю портфолио работ Drukar (13 фото)...")
    
    # Telegram поддерживает до 10 фото в одном сообщении, поэтому делим 13 фото на 2 пачки
    album1 = [types.InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    album2 = [types.InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(11, 14)]
    
    try:
        await callback.message.answer_media_group(media=album1)
        await asyncio.sleep(0.5)
        await callback.message.answer_media_group(media=album2)
    except Exception as e:
        logging.error(f"Ошибка галереи: {e}")
        await callback.message.answer("⚠️ Некоторые фото еще подгружаются. Попробуйте через мгновение!")
    
    await callback.answer()

async def main():
    logging.info("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())