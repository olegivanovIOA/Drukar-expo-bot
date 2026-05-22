import os
import asyncio
import logging
import random
import httpx
import openai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, BotCommand, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
B24_WEBHOOK = "https://b24-733cj8.bitrix24.eu/rest/2517/w9ibissc7lvshipw"
SHEETS_WEBHOOK = "https://script.google.com/macros/s/AKfycbxNRquK7qf46_Ww933xyjUJqRyNa4eAcfD2hA-aXBxSLjAEcEqJM9O7evIYYtEcQ32wag/exec"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
ai_client = openai.OpenAI(api_key=OPENAI_KEY)

GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"
purchase_attempts = 0

CONTACT_EMAIL = "sales@drukar.com"
STAND_INFO = "Стенд A-45, Павільйон №2, МВЦ, Київ"
EXPO_NAME = "Addit EXPO 3D-2026"
B24_SOURCE = "Telegram - DRUKAR_AdditExpo2026_bot"
SITE_URL = "https://www.3drukar.com/ua/home-українська/"


# --- FSM ---
class ManualVCard(StatesGroup):
    name = State()
    company = State()
    position = State()
    phone = State()
    email = State()
    website = State()
    notes = State()


# --- Google Sheets ---
async def save_to_sheets(contact: dict, source_type: str = "manual") -> bool:
    payload = {
        "name": contact.get("name", ""),
        "company": contact.get("company", ""),
        "position": contact.get("position", ""),
        "phone": contact.get("phone", ""),
        "email": contact.get("email", ""),
        "website": contact.get("website", ""),
        "notes": contact.get("notes", ""),
        "source": "Ручний ввід менеджера" if source_type == "manual" else "Розпізнавання візитки (AI)"
    }
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.post(SHEETS_WEBHOOK, json=payload)
            result = r.json()
            if result.get("status") == "ok":
                logging.info("Sheets: контакт збережено")
                return True
            else:
                logging.error(f"Sheets error: {result}")
                return False
    except Exception as e:
        logging.error(f"Sheets request failed: {e}")
        return False


# --- Bitrix24 ---
async def create_b24_deal(contact: dict, source_type: str = "manual") -> bool:
    title = f"[{EXPO_NAME}] {contact.get('name', 'Невідомий')} — {contact.get('company', '')}"
    comments_parts = []
    if contact.get("phone"):
        comments_parts.append(f"Телефон: {contact['phone']}")
    if contact.get("email"):
        comments_parts.append(f"Email: {contact['email']}")
    if contact.get("position"):
        comments_parts.append(f"Посада: {contact['position']}")
    if contact.get("website"):
        comments_parts.append(f"Сайт: {contact['website']}")
    if contact.get("notes"):
        comments_parts.append(f"Примітки: {contact['notes']}")
    comments_parts.append(f"Джерело: {'Ручний ввід менеджера' if source_type == 'manual' else 'Розпізнавання візитки (AI)'}")
    comments_parts.append(f"Захід: {EXPO_NAME}")

    fields = {
        "TITLE": title,
        "STAGE_ID": "NEW",
        "CATEGORY_ID": 0,
        "SOURCE_ID": "WEBFORM",
        "SOURCE_DESCRIPTION": B24_SOURCE,
        "COMMENTS": "\n".join(comments_parts),
        "TYPE_ID": "SALE",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{B24_WEBHOOK}/crm.deal.add.json", json=payload)
            data = r.json()
            if data.get("result"):
                logging.info(f"B24 Deal created: ID={data['result']}")
                return True
            else:
                logging.error(f"B24 error: {data}")
                return False
    except Exception as e:
        logging.error(f"B24 request failed: {e}")
        return False


# --- Меню ---
async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Головне меню 🚀"),
        BotCommand(command="/find_us", description="Де наш стенд? 📍"),
        BotCommand(command="/buy", description="Придбати котушку 🛒"),
        BotCommand(command="/vcard", description="Контакт DRUKAR 📇"),
        BotCommand(command="/manual_contact", description="Ввести контакт вручну ✍️"),
    ]
    await bot.set_my_commands(commands)


def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url=SITE_URL))
    builder.row(InlineKeyboardButton(text="🛒 Придбати котушку", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="📍 Де наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея робіт", callback_data="gallery"))
    builder.row(InlineKeyboardButton(text="📇 Зберегти контакт DRUKAR", callback_data="get_vcard"))
    builder.row(InlineKeyboardButton(text="📸 Надіслати візитку (AI)", callback_data="scan_card"))
    builder.row(InlineKeyboardButton(text="✍️ Ввести контакт вручну", callback_data="manual_contact"))
    return builder.as_markup()


# --- /start ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вітаємо на стенді *DRUKAR*! 🇺🇦\n\n"
        "Ми — український виробник матеріалів для 3D-друку.\n"
        "Спеціалізуємось на оптових постачаннях та якості для професіоналів.\n\n"
        "📸 *Надішліть фото візитки* — я миттєво розпізнаю її за допомогою ШІ!\n"
        f"✉️ Або пишіть нам: {CONTACT_EMAIL}",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


# --- Розпізнавання візиток ---
@dp.callback_query(F.data == "scan_card")
async def ask_for_card(callback: types.CallbackQuery):
    await callback.message.answer(
        "📸 Надішліть фото візитки.\n"
        "Я розпізнаю ім'я, компанію, телефони та автоматично створю угоду в CRM!"
    )
    await callback.answer()


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not OPENAI_KEY:
        return await message.answer("⚠️ Помилка: API ключ OpenAI не налаштований.")

    status_msg = await message.answer("🔍 Вивчаю візитку... Зачекайте кілька секунд.")
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    prompt = (
        "Ти — експерт з розпізнавання візиток. Виписати ВСІ дані: ім'я, прізвище, компанія, "
        "посада, телефони, сайти, соцмережі. Оформи українською. "
        "Окремим блоком в кінці дай JSON:\n"
        "```json\n{\"name\": \"\", \"company\": \"\", \"position\": \"\", \"phone\": \"\", \"email\": \"\", \"website\": \"\", \"notes\": \"\"}\n```"
    )

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": file_url}}
            ]}],
            max_tokens=900
        )
        full_text = response.choices[0].message.content

        import json, re
        contact = {"name": "", "company": "", "position": "", "phone": "", "email": "", "website": "", "notes": ""}
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', full_text, re.DOTALL)
        if json_match:
            try:
                contact = json.loads(json_match.group(1))
            except Exception:
                pass
            display_text = full_text[:json_match.start()].strip()
        else:
            display_text = full_text

        await status_msg.edit_text(
            f"✅ *Дані візитки:*\n\n{display_text}\n\n⏳ Зберігаю...",
            parse_mode="Markdown"
        )

        b24_ok, sheets_ok = await asyncio.gather(
            create_b24_deal(contact, source_type="photo"),
            save_to_sheets(contact, source_type="photo")
        )

        parts = []
        if b24_ok: parts.append("✅ Битрікс24")
        if sheets_ok: parts.append("✅ Google Sheets")
        result_text = f"Збережено: {', '.join(parts)}" if parts else "⚠️ Не вдалось зберегти автоматично."
        await message.answer(result_text)

    except Exception as e:
        logging.error(f"AI Error: {e}")
        await status_msg.edit_text("❌ Складна візитка! Спробуйте сфотографувати ближче.")


# --- Ручний ввід ---
@dp.message(Command("manual_contact"))
@dp.callback_query(F.data == "manual_contact")
async def start_manual_vcard(event, state: FSMContext):
    message = event if isinstance(event, types.Message) else event.message
    await state.clear()
    await state.set_state(ManualVCard.name)
    await message.answer(
        "✍️ *Ручний ввід контакту*\n\n"
        "Введіть *ім'я та прізвище*:\n_(або — щоб пропустити)_",
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()


@dp.message(ManualVCard.name)
async def vcard_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text if message.text != "—" else "")
    await state.set_state(ManualVCard.company)
    await message.answer("🏢 *Назва компанії:*", parse_mode="Markdown")

@dp.message(ManualVCard.company)
async def vcard_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text if message.text != "—" else "")
    await state.set_state(ManualVCard.position)
    await message.answer("💼 *Посада:*", parse_mode="Markdown")

@dp.message(ManualVCard.position)
async def vcard_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text if message.text != "—" else "")
    await state.set_state(ManualVCard.phone)
    await message.answer("📞 *Телефон:*", parse_mode="Markdown")

@dp.message(ManualVCard.phone)
async def vcard_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text if message.text != "—" else "")
    await state.set_state(ManualVCard.email)
    await message.answer("✉️ *Email:*", parse_mode="Markdown")

@dp.message(ManualVCard.email)
async def vcard_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text if message.text != "—" else "")
    await state.set_state(ManualVCard.website)
    await message.answer("🌐 *Сайт / соцмережі:*", parse_mode="Markdown")

@dp.message(ManualVCard.website)
async def vcard_website(message: types.Message, state: FSMContext):
    await state.update_data(website=message.text if message.text != "—" else "")
    await state.set_state(ManualVCard.notes)
    await message.answer("📝 *Примітки:*\n_(або — щоб пропустити)_", parse_mode="Markdown")

@dp.message(ManualVCard.notes)
async def vcard_notes(message: types.Message, state: FSMContext):
    await state.update_data(notes=message.text if message.text != "—" else "")
    data = await state.get_data()
    await state.clear()

    summary = (
        f"📋 *Підсумок:*\n\n"
        f"👤 {data.get('name') or '—'}\n"
        f"🏢 {data.get('company') or '—'}\n"
        f"💼 {data.get('position') or '—'}\n"
        f"📞 {data.get('phone') or '—'}\n"
        f"✉️ {data.get('email') or '—'}\n"
        f"🌐 {data.get('website') or '—'}\n"
        f"📝 {data.get('notes') or '—'}\n\n"
        f"⏳ Зберігаю..."
    )
    await message.answer(summary, parse_mode="Markdown")

    b24_ok, sheets_ok = await asyncio.gather(
        create_b24_deal(data, source_type="manual"),
        save_to_sheets(data, source_type="manual")
    )

    parts = []
    if b24_ok: parts.append("✅ Битрікс24")
    if sheets_ok: parts.append("✅ Google Sheets")

    if parts:
        await message.answer(f"Збережено: {', '.join(parts)}", reply_markup=get_main_menu())
    else:
        await message.answer(f"⚠️ Не вдалось зберегти. Напишіть на {CONTACT_EMAIL}", reply_markup=get_main_menu())


# --- Контакт DRUKAR ---
@dp.message(Command("vcard"))
@dp.callback_query(F.data == "get_vcard")
async def send_vcard(event):
    message = event if isinstance(event, types.Message) else event.message
    vcard_data = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:DRUKAR | 3D Друк\nORG:DRUKAR\n"
        "TITLE:Виробник філаменту\nTEL;TYPE=WORK,VOICE:+380991234567\n"
        f"EMAIL:{CONTACT_EMAIL}\nURL:{SITE_URL}\n"
        f"NOTE:{STAND_INFO} | {EXPO_NAME}\nEND:VCARD"
    )
    await message.answer_contact(phone_number="+380991234567", first_name="DRUKAR",
                                  last_name="3D Materials", vcard=vcard_data)
    await message.answer(
        f"👆 Натисніть на картку → *Створити новий контакт*\n\n"
        f"✉️ {CONTACT_EMAIL}\n🌐 {SITE_URL}\n📍 {STAND_INFO}",
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# --- Купити ---
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
            f"🔥 *Хіт виставки!*\n"
            f"Цю котушку сьогодні обрали вже *{display_count}* раз(ів).\n\n"
            f"🛒 *Оплата на ФОП*\n"
            f"Відскануйте код вище та надішліть квитанцію в цей чат.\n\n"
            f"📍 {STAND_INFO}\n✉️ {CONTACT_EMAIL}"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# --- Де стенд ---
@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}event_preview.jpg",
        caption=(
            f"📍 *DRUKAR на {EXPO_NAME}*\n\n"
            f"🏢 Київ, МВЦ (Броварський пр-т, 15)\n"
            f"✅ {STAND_INFO}\n\n"
            f"✉️ {CONTACT_EMAIL}\n"
            f"🔗 [Офіційний сайт виставки](https://www.iec-expo.com.ua/addit-2026.html)"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# --- Галерея ---
@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Завантажую галерею...")
    album = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    try:
        await callback.message.answer_media_group(media=album)
    except Exception:
        await callback.message.answer("⚠️ Спробуйте за кілька секунд.")
    await callback.answer()


# --- ЗАПУСК (polling) ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_main_menu(bot)
    logging.info("DRUKAR Bot запущено! 🇺🇦")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинено")
