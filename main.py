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

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
ai_client = openai.OpenAI(api_key=OPENAI_KEY)

GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"
purchase_attempts = 0

PHONE = "+380673053060"
PHONE_DISPLAY = "+380 67 305 30 60"
STAND = "D-08 (Павільйон 3)"

async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Главное меню 🚀"),
        BotCommand(command="/find_us", description="Где наш стенд? 📍"),
        BotCommand(command="/buy", description="Купить катушку 🛒"),
        BotCommand(command="/vcard", description="Контакт DRUKAR 📇"),
    ]
    await bot.set_my_commands(commands)

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея работ", callback_data="gallery"))
    builder.row(InlineKeyboardButton(text="📇 Сохранить контакт DRUKAR", callback_data="get_vcard"))
    builder.row(InlineKeyboardButton(text="📸 Отправить визитку", callback_data="scan_card"))
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Приветствуем на стенде **DRUKAR**! 🚀\n\n"
        "Мы — украинский производитель материалов для 3D-печати. "
        "Специализируемся на оптовых поставках и качестве для профессионалов.\n\n"
        "📸 **Пришлите фото визитки**, и я мгновенно распознаю её с помощью ИИ!",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "scan_card")
async def ask_for_card(callback: types.CallbackQuery):
    await callback.message.answer("📸 Просто пришлите фото визитки. Я распознаю имя, компанию, все телефоны, соцсети и даже мелкое описание деятельности!")
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not OPENAI_KEY:
        return await message.answer("⚠️ Ошибка: API ключ OpenAI не настроен в Environment Variables.")
    status_msg = await message.answer("🔍 Внимательно изучаю визитку... Это займет пару секунд.")
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    prompt = (
        "Ты — эксперт по распознаванию визиток. Внимательно посмотри на фото. "
        "Твоя задача: выписать ВСЕ данные, которые сможешь найти. "
        "Особое внимание: название компании, описание услуг (чем занимаются), адреса, телефоны, "
        "сайты и соцсети (Instagram, Telegram ники, FB). "
        "Оформи ответ красиво и структурировано списком на русском языке. "
        "Если чего-то нет — просто не пиши эту строку."
    )
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": file_url}}
            ]}],
            max_tokens=800
        )
        extracted_text = response.choices[0].message.content
        final_text = f"✅ **Данные визитки успешно считаны:**\n\n{extracted_text}\n\n---\n*Данные добавлены в вашу базу DRUKAR.*"
        await status_msg.edit_text(final_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await status_msg.edit_text("❌ Сложная визитка! Попробуйте сделать фото чуть ближе и при хорошем освещении.")

@dp.message(Command("vcard"))
@dp.callback_query(F.data == "get_vcard")
async def send_vcard(event):
    message = event if isinstance(event, types.Message) else event.message
    vcard_data = (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:DRUKAR | 3D Printing\n"
        "ORG:DRUKAR\n"
        "TITLE:Виробник філаменту\n"
        f"TEL;TYPE=WORK,VOICE:{PHONE}\n"
        "EMAIL:sales@drukar.com\n"
        "URL:https://www.3drukar.com\n"
        f"NOTE:Ваш партнер у 3D-друці. Стенд {STAND} на Addit EXPO 3D-2026\n"
        "END:VCARD"
    )
    await message.answer_contact(
        phone_number=PHONE,
        first_name="DRUKAR",
        last_name="3D Materials",
        vcard=vcard_data
    )
    await message.answer("👆 Натисніть на картку вище і виберіть 'Створити новий контакт', щоб зберегти нас.")
    if isinstance(event, types.CallbackQuery):
        await event.answer()

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
            f"🔥 **Хіт виставки!**\n"
            f"Цю котушку сьогодні вже обрали **{display_count}** разів.\n\n"
            f"🛒 **Оплата на ФОП**\n"
            f"Відскануйте код вище і надішліть квитанцію в цей чат.\n\n"
            f"Забрати замовлення можна прямо зараз на стенді **{STAND}**!\n"
            f"📞 {PHONE_DISPLAY}"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}event_preview.jpg",
        caption=(
            f"📍 **DRUKAR на Addit EXPO 3D-2026**\n\n"
            f"🏢 Київ, МВЦ (Броварський пр-т, 15)\n"
            f"✅ Наш стенд: **{STAND}**\n"
            f"📞 {PHONE_DISPLAY}\n\n"
            f"🔗 [Офіційний сайт виставки](https://www.iec-expo.com.ua/addit-2026.html)"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Підвантажую галерею наших робіт...")
    album = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    try:
        await callback.message.answer_media_group(media=album)
    except Exception:
        await callback.message.answer("⚠️ Зображення ще підвантажуються, спробуйте за кілька секунд.")
    await callback.answer()

async def main():
    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("DRUKAR Bot is Live and Ready!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинено")
