import os
import asyncio
import logging
import random
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

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Путь к вашим медиа-файлам на GitHub
GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

# Глобальный счетчик попыток покупки (сбрасывается при перезапуске сервера)
purchase_attempts = 0

# --- НАСТРОЙКА МЕНЮ КОМАНД ---
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Главное меню 🚀"),
        BotCommand(command="/find_us", description="Где наш стенд? 📍"),
        BotCommand(command="/buy", description="Купить катушку 🛒"),
        BotCommand(command="/gallery", description="Галерея работ 📸"),
    ]
    await bot.set_my_commands(main_menu_commands)
    logging.info("Меню команд Telegram обновлено")

# --- ГЛАВНОЕ ИНЛАЙН-МЕНЮ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    
    # Ссылки
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", url="https://calendly.com/ioa4/30min"))
    
    # Кнопки с внутренней логикой
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея работ", callback_data="gallery"))
    
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Приветствуем на стенде **Drukar**! 🚀\n\n"
        f"Мы — украинский производитель инженерных материалов для 3D-печати[cite: 1].\n"
        f"Специализируемся на оптовых поставках и качественном филаменте[cite: 1].\n\n"
        f"Чем я могу вам помочь?",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    photo_url = GITHUB_BASE_URL + "event_preview.jpg" # Картинка-анонс выставки[cite: 1]
    
    caption_text = (
        "📍 **DRUKAR на Addit EXPO 3D-2026**[cite: 1]\n\n"
        "📅 26-28 мая 2026 года[cite: 1]\n"
        "🏢 Киев, МВЦ (Броварской пр-т, 15)[cite: 1]\n"
        "✅ Наш стенд: **A-45 (Павильон №2)**\n\n"
        "Официальная страница выставки:\n"
        "🔗 https://www.iec-expo.com.ua/addit-2026.html"
    )
    
    try:
        await message.answer_photo(
            photo=photo_url,
            caption=caption_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки фото выставки: {e}")
        await message.answer(caption_text, disable_web_page_preview=False)
        
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.message(Command("buy"))
@dp.callback_query(F.data == "buy_filament")
async def cmd_buy(event):
    global purchase_attempts
    message = event if isinstance(event, types.Message) else event.message
    
    # Маркетинговое приукрашивание
    purchase_attempts += random.randint(1, 3)
    display_count = 142 + purchase_attempts # Базовое число 142 + клики

    qr_url = GITHUB_BASE_URL + "qr_payment.png"
    
    caption_text = (
        f"🔥 **Популярный выбор!**\n"
        f"Эту катушку сегодня выбрали уже **{display_count}** раз(а).\n\n"
        f"🛒 **Оплата заказа (ФОП)**\n"
        f"1. Отсканируйте QR-код выше для оплаты.\n"
        f"2. Пришлите скриншот квитанции в этот чат.\n\n"
        f"Ваш заказ будет подготовлен к выдаче на стенде A-45![cite: 1]"
    )
    
    try:
        await message.answer_photo(
            photo=qr_url,
            caption=caption_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки QR: {e}")
        await message.answer("⚠️ Изображение QR-кода сейчас недоступно. Пожалуйста, обратитесь к менеджеру на стенде.")

    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Загружаю портфолио работ Drukar (13 фото)...")
    
    album1 = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    album2 = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(11, 14)]
    
    try:
        await callback.message.answer_media_group(media=album1)
        await asyncio.sleep(0.5)
        await callback.message.answer_media_group(media=album2)
    except Exception as e:
        logging.error(f"Ошибка галереи: {e}")
        await callback.message.answer("⚠️ Фотографии галереи подгружаются, попробуйте через минуту.")
    
    await callback.answer()

# --- ЗАПУСК БОТА ---
async def main():
    # Настройка команд в интерфейсе Telegram
    await set_main_menu(bot)
    
    logging.info("Бот Drukar готов к работе!")
    
    # Принудительное удаление вебхука перед началом Polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск опроса обновлений
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")