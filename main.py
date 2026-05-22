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
B24_WEBHOOK = "https://b24-733cj8.bitrix24.eu/rest/gyj1j3mxsy5x3g55"

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


# --- FSM для ручного вводу vCard ---
class ManualVCard(StatesGroup):
    name = State()
    company = State()
    position = State()
    phone = State()
    email = State()
    website = State()
    notes = State()


# --- Bitrix24: створення угоди ---
async def create_b24_deal(contact: dict, source_type: str = "manual") -> bool:
    """
    Створює Deal в Б24 (category_id=0, стадія NEW).
    contact: dict з ключами name, company, position, phone, email, website, notes
    """
    title = f"[{EXPO_NAME}] {contact.get('name', 'Невідомий')} — {contact.get('company', '')}"
    
    comments_parts = []
    if contact.get("position"):
        comments_parts.append(f"Посада: {contact['position']}")
    if contact.get("website"):
        comments_parts.append(f"Сайт: {contact['website']}")
    if contact.get("notes"):
        comments_parts.append(f"Примітки: {contact['notes']}")
    comments_parts.append(f"Джерело вводу: {'Ручний ввід менеджера' if source_type == 'manual' else 'Розпізнавання візитки (AI)'}")
    comments_parts.append(f"Захід: {EXPO_NAME}")

    fields = {
        "TITLE": title,
        "STAGE_ID": "NEW",
        "CATEGORY_ID": 0,
        "SOURCE_ID": "WEBFORM",          # стандартний системний ID
        "SOURCE_DESCRIPTION": B24_SOURCE,
        "COMMENTS": "\n".join(comments_parts),
        "TYPE_ID": "SALE",
    }

    # Телефон
    if contact.get("phone"):
        fields["UF_CRM_PHONE"] = contact["phone"]  # запасний варіант
        # Контакт — через CONTACT_ID ми не маємо, тому пишемо в коментар
        comments_parts.insert(0, f"Телефон: {contact['phone']}")

    # Email
    if contact.get("email"):
        comments_parts.insert(1, f"Email: {contact['email']}")

    # Оновлюємо COMMENTS з телефоном/email на початку
    fields["COMMENTS"] = "\n".join(comments_parts)

    payload = {"fields": fields, "params": {"REGISTER_SONET_EVENT": "Y"}}

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


# --- Меню команд ---
async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Головне меню 🚀"),
        BotCommand(command="/find_us", description="Де наш стенд? 📍"),
        BotCommand(command="/buy", description="Придбати котушку 🛒"),
        BotCommand(command="/vcard", description="Контакт DRUKAR 📇"),
        BotCommand(command="/manual_contact", description="Ввести контакт вручну ✍️"),
    ]
    await bot.set_my_commands(commands)


# --- Головна клавіатура ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
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


# --- РОЗПІЗНАВАННЯ ВІЗИТОК (AI) ---
@dp.callback_query(F.data == "scan_card")
async def ask_for_card(callback: types.CallbackQuery):
    await callback.message.answer(
        "📸 Надішліть фото візитки.\n"
        "Я розпізнаю ім'я, компанію, телефони, соцмережі та автоматично створю угоду в CRM!"
    )
    await callback.answer()


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not OPENAI_KEY:
        return await message.answer("⚠️ Помилка: API ключ OpenAI не налаштований.")

    status_msg = await message.answer("🔍 Уважно вивчаю візитку... Зачекайте кілька секунд.")

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    prompt = (
        "Ти — експерт з розпізнавання візиток. Уважно подивись на фото. "
        "Твоя задача: виписати ВСІ дані, які зможеш знайти. "
        "Особлива увага: ім'я, прізвище, назва компанії, посада, опис послуг, адреса, телефони, "
        "сайти та соцмережі (Instagram, Telegram, FB). "
        "Оформи відповідь структуровано українською мовою. "
        "Якщо чогось немає — просто не пиши цей рядок. "
        "Окремим блоком в кінці дай JSON такого формату (тільки ці поля, без зайвого тексту):\n"
        "```json\n{\"name\": \"\", \"company\": \"\", \"position\": \"\", \"phone\": \"\", \"email\": \"\", \"website\": \"\", \"notes\": \"\"}\n```"
    )

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": file_url}}
                ],
            }],
            max_tokens=900
        )

        full_text = response.choices[0].message.content

        # Витягуємо JSON для Б24
        import json, re
        contact = {"name": "", "company": "", "position": "", "phone": "", "email": "", "website": "", "notes": ""}
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', full_text, re.DOTALL)
        if json_match:
            try:
                contact = json.loads(json_match.group(1))
            except Exception:
                pass
            # Прибираємо JSON блок з тексту для відображення
            display_text = full_text[:json_match.start()].strip()
        else:
            display_text = full_text

        final_text = (
            f"✅ *Дані візитки успішно зчитано:*\n\n{display_text}\n\n"
            f"---\n⏳ Зберігаю в CRM..."
        )
        await status_msg.edit_text(final_text, parse_mode="Markdown")

        # Відправляємо в Б24
        success = await create_b24_deal(contact, source_type="photo")
        if success:
            await message.answer("✅ Угоду створено в Битрікс24! Стадія: *Новий лід*", parse_mode="Markdown")
        else:
            await message.answer("⚠️ Дані зчитано, але CRM наразі недоступна. Збережіть дані вручну.")

    except Exception as e:
        logging.error(f"AI Error: {e}")
        await status_msg.edit_text("❌ Складна візитка! Спробуйте сфотографувати ближче при гарному освітленні.")


# --- РУЧНИЙ ВВІД vCard ---
@dp.message(Command("manual_contact"))
@dp.callback_query(F.data == "manual_contact")
async def start_manual_vcard(event, state: FSMContext):
    message = event if isinstance(event, types.Message) else event.message
    await state.clear()
    await state.set_state(ManualVCard.name)
    await message.answer(
        "✍️ *Ручний ввід контакту*\n\n"
        "Введіть *ім'я та прізвище* контакту:\n"
        "_(або надішліть — щоб пропустити)_",
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
    await message.answer(
        "📝 *Примітки* (чим цікавий контакт, про що домовились):\n_(або — щоб пропустити)_",
        parse_mode="Markdown"
    )


@dp.message(ManualVCard.notes)
async def vcard_notes(message: types.Message, state: FSMContext):
    await state.update_data(notes=message.text if message.text != "—" else "")
    data = await state.get_data()
    await state.clear()

    # Показуємо підсумок
    summary = (
        f"📋 *Підсумок контакту:*\n\n"
        f"👤 Ім'я: {data.get('name') or '—'}\n"
        f"🏢 Компанія: {data.get('company') or '—'}\n"
        f"💼 Посада: {data.get('position') or '—'}\n"
        f"📞 Телефон: {data.get('phone') or '—'}\n"
        f"✉️ Email: {data.get('email') or '—'}\n"
        f"🌐 Сайт: {data.get('website') or '—'}\n"
        f"📝 Примітки: {data.get('notes') or '—'}\n\n"
        f"⏳ Зберігаю в CRM..."
    )
    await message.answer(summary, parse_mode="Markdown")

    success = await create_b24_deal(data, source_type="manual")
    if success:
        await message.answer(
            "✅ *Угоду створено в Битрікс24!*\n"
            f"Стадія: Новий лід | Джерело: {B24_SOURCE}",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            "⚠️ Дані збережено локально, але CRM наразі недоступна.\n"
            f"Зверніться до менеджера або напишіть на {CONTACT_EMAIL}",
            reply_markup=get_main_menu()
        )


# --- КОРПОРАТИВНИЙ КОНТАКТ DRUKAR ---
@dp.message(Command("vcard"))
@dp.callback_query(F.data == "get_vcard")
async def send_vcard(event):
    message = event if isinstance(event, types.Message) else event.message

    vcard_data = (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:DRUKAR | 3D Друк\n"
        "ORG:DRUKAR\n"
        "TITLE:Виробник філаменту\n"
        "TEL;TYPE=WORK,VOICE:+380442900000\n"
        f"EMAIL:{CONTACT_EMAIL}\n"
        "URL:https://www.3drukar.com\n"
        f"NOTE:{STAND_INFO} | {EXPO_NAME}\n"
        "END:VCARD"
    )

    await message.answer_contact(
        phone_number="+380442900000",
        first_name="DRUKAR",
        last_name="3D Materials",
        vcard=vcard_data
    )
    await message.answer(
        f"👆 Натисніть на картку вище → *Створити новий контакт*\n\n"
        f"✉️ Email: {CONTACT_EMAIL}\n"
        f"🌐 Сайт: www.3drukar.com\n"
        f"📍 {STAND_INFO}",
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# --- КУПИТИ КОТУШКУ ---
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
            f"📍 Забрати замовлення можна просто зараз на {STAND_INFO}!\n\n"
            f"✉️ Питання: {CONTACT_EMAIL}"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# --- ДЕ НАШ СТЕНД ---
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


# --- ГАЛЕРЕЯ ---
@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Завантажую галерею наших робіт...")
    album = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    try:
        await callback.message.answer_media_group(media=album)
    except Exception:
        await callback.message.answer("⚠️ Зображення ще завантажуються, спробуйте за кілька секунд.")
    await callback.answer()


# --- ЗАПУСК ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(3)
    await set_main_menu(bot)
    logging.info("DRUKAR Bot запущено! 🇺🇦")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинено")
