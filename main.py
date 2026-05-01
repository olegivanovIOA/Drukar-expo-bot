import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КНОПКИ МЕНЮ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://drukar.com.ua")) # Укажите ваш сайт
    builder.row(InlineKeyboardButton(text="🛒 Купить тестовую катушку", url="https://drukar.com.ua/shop"))
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", callback_data="make_meeting"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="💎 Галерея работ", callback_data="gallery"))
    return builder.as_markup()

def get_contact_btn():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт менеджеру", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Уведомление админу о новом посетителе
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"🔔 Новый пользователь в боте: @{message.from_user.username} ({message.from_user.full_name})")
    
    await message.answer(
        f"Приветствуем, {message.from_user.first_name}, на стенде **Drukar**! 🚀\n\n"
        "Мы производим профессиональные филаменты для 3D-печати.\n"
        "Чем я могу помочь вам сегодня?",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "find_us")
async def find_us(callback: types.CallbackQuery):
    await callback.message.answer(
        "📍 **Мы находимся в Павильоне №2, стенд A-45.**\n\n"
        "Ищите ярко-синий стенд с логотипом Drukar и напечатанными деталями двигателей!",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "make_meeting")
async def meeting(callback: types.CallbackQuery):
    await callback.message.answer(
        "Чтобы забронировать время для встречи с нашим инженером, "
        "нажмите кнопку ниже и поделитесь контактом. Мы сразу перезвоним!",
        reply_markup=get_contact_btn()
    )
    await callback.answer()

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    # Отправляем контакт вам в личку
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID, 
            f"🔥 **НОВАЯ ЗАЯВКА НА ВСТРЕЧУ**\n"
            f"Имя: {message.contact.first_name}\n"
            f"Телефон: {message.contact.phone_number}",
            parse_mode="Markdown"
        )
    await message.answer("✅ Спасибо! Мы получили ваши данные и свяжемся с вами в ближайшее время.", reply_markup=types.ReplyKeyboardRemove())

@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    # Пример отправки фото (замените URL на реальные фото ваших изделий)
    await callback.message.answer("📸 Загружаю примеры печати из нашего Carbon-PA...")
    # Здесь можно отправить медиа-группу (альбом)
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
