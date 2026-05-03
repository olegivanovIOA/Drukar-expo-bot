import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Путь к вашим медиа-файлам на GitHub
GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

# --- ФУНКЦИЯ НАСТРОЙКИ МЕНЮ (КНОПКА СЛЕВА) ---
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Запустить бота 🚀"),
        BotCommand(command="/find_us", description="Где наш стенд? 📍"),
        BotCommand(command="/gallery", description="Галерея работ 📸"),
        BotCommand(command="/site", description="Наш сайт 🌐")
    ]
    await bot.set_my_commands(main_menu_commands)
    logging.info("Меню команд успешно обновлено в Telegram")

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", url="https://calendly.com/ioa4/30min"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", url="https://www.3drukar.com/shop"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея работ", callback_data="gallery"))
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

# Обработка команд из меню (текстовых)
@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    # Универсальный обработчик для команды и кнопки
    message = event if isinstance(event, types.Message) else event.message
    photo_url = GITHUB_BASE_URL + "map.jpg"
    await message.answer_photo(
        photo=photo_url,
        caption="📍 **Мы в Павильоне №2, стенд A-45.**\nЖдем вас!",
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.message(Command("gallery"))
@dp.callback_query(F.data == "gallery")
async def show_gallery(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer("📸 Загружаю портфолио работ Drukar (13 фото)...")
    
    album1 = [types.InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    album2 = [types.InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(11, 14)]
    
    try:
        await message.answer_media_group(media=album1)
        await asyncio.sleep(0.5)
        await message.answer_media_group(media=album2)
    except Exception as e:
        logging.error(f"Ошибка галереи: {e}")
        await message.answer("⚠️ Некоторые фото подгружаются. Попробуйте через мгновение!")
    
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.message(Command("site"))
async def cmd_site(message: types.Message):
    await message.answer("Переходите на наш официальный сайт: https://www.3drukar.com")

async def main():
    # Регистрация меню при старте
    await set_main_menu(bot)
    logging.info("Бот запущен и готов к работе!")
    
    # Удаляем вебхук на случай, если он остался от старого Web Service
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
