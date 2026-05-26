# -*- coding: utf-8 -*-
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
PAY_URL = "https://bank.gov.ua/qr/QkNECjAwMgoxClVDVAoK0KTQntCfINCb0L7QsdC-0LLQsCDQkNC90L3QsCDQktCw0LvQtdGA0ZbRl9Cy0L3QsApVQTA4MzIyMDAxMDAwMDAyNjAwODM4MDAwMjg5OQoKMzQ1ODIwMjU0NwoKCgoK"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
ai_client = openai.OpenAI(api_key=OPENAI_KEY)

GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

CONTACT_EMAIL = "sales@drukar.com"
STAND_INFO = "Стенд D-08, Павільйон 3, МВЦ, Київ"
EXPO_NAME = "Addit EXPO 3D-2026"
B24_SOURCE = "Telegram - DRUKAR_AdditExpo2026_bot"
SITE_URL = "https://www.3drukar.com/ua/home-%D1%83%D0%BA%D1%80%D0%B0%D1%97%D0%BD%D1%81%D1%8C%D0%BA%D0%B0/"


class ManualVCard(StatesGroup):
    name = State()
    company = State()
    position = State()
    phone = State()
    email = State()
    website = State()
    notes = State()


async def save_to_sheets(contact: dict, source_type: str = "manual") -> bool:
    payload = {
        "name": contact.get("name", ""),
        "company": contact.get("company", ""),
        "position": contact.get("position", ""),
        "phone": contact.get("phone", ""),
        "email": contact.get("email", ""),
        "website": contact.get("website", ""),
        "notes": contact.get("notes", ""),
        "source": "\u0420\u0443\u0447\u043d\u0438\u0439 \u0432\u0432\u0456\u0434 \u043c\u0435\u043d\u0435\u0434\u0436\u0435\u0440\u0430" if source_type == "manual" else "\u0420\u043e\u0437\u043f\u0456\u0437\u043d\u0430\u0432\u0430\u043d\u043d\u044f \u0432\u0456\u0437\u0438\u0442\u043a\u0438 (AI)"
    }
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.post(SHEETS_WEBHOOK, json=payload)
            result = r.json()
            if result.get("status") == "ok":
                logging.info("Sheets: OK")
                return True
            else:
                logging.error(f"Sheets error: {result}")
                return False
    except Exception as e:
        logging.error(f"Sheets failed: {e}")
        return False


async def get_and_increment_counter() -> int:
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.get(SHEETS_WEBHOOK + "?action=counter")
            data = r.json()
            count = int(data.get("counter", 87))
            new_count = count + random.randint(1, 4)
            await client.post(SHEETS_WEBHOOK, json={"action": "set_counter", "value": new_count})
            return new_count
    except Exception as e:
        logging.error(f"Counter error: {e}")
        return random.randint(89, 165)


async def create_b24_deal(contact: dict, source_type: str = "manual") -> bool:
    name = contact.get("name", "Unknown")
    company = contact.get("company", "")
    title = f"[{EXPO_NAME}] {name} - {company}"
    lines = []
    if contact.get("phone"): lines.append(f"Phone: {contact['phone']}")
    if contact.get("email"): lines.append(f"Email: {contact['email']}")
    if contact.get("position"): lines.append(f"Position: {contact['position']}")
    if contact.get("website"): lines.append(f"Website: {contact['website']}")
    if contact.get("notes"): lines.append(f"Notes: {contact['notes']}")
    lines.append(f"Source: {'Manual' if source_type == 'manual' else 'AI card scan'}")
    lines.append(f"Event: {EXPO_NAME}")

    fields = {
        "TITLE": title,
        "STAGE_ID": "NEW",
        "CATEGORY_ID": 0,
        "SOURCE_ID": "7|TELEGRAM",
        "SOURCE_DESCRIPTION": B24_SOURCE,
        "COMMENTS": "\n".join(lines),
        "TYPE_ID": "SALE",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{B24_WEBHOOK}/crm.deal.add.json", json={"fields": fields})
            data = r.json()
            if data.get("result"):
                logging.info(f"B24 Deal created: {data['result']}")
                return True
            else:
                logging.error(f"B24 error: {data}")
                return False
    except Exception as e:
        logging.error(f"B24 failed: {e}")
        return False


async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="/start", description="\u0413\u043e\u043b\u043e\u0432\u043d\u0435 \u043c\u0435\u043d\u044e"),
        BotCommand(command="/find_us", description="\u0414\u0435 \u043d\u0430\u0448 \u0441\u0442\u0435\u043d\u0434?"),
        BotCommand(command="/buy", description="\u041f\u0440\u0438\u0434\u0431\u0430\u0442\u0438 \u043a\u043e\u0442\u0443\u0448\u043a\u0443"),
        BotCommand(command="/vcard", description="\u041a\u043e\u043d\u0442\u0430\u043a\u0442 DRUKAR"),
        BotCommand(command="/manual_contact", description="\u0412\u0432\u0435\u0441\u0442\u0438 \u043a\u043e\u043d\u0442\u0430\u043a\u0442 \u0432\u0440\u0443\u0447\u043d\u0443"),
    ]
    await bot.set_my_commands(commands)


def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="\U0001f310 \u041d\u0430\u0448 \u0441\u0430\u0439\u0442", url=SITE_URL))
    builder.row(InlineKeyboardButton(text="\U0001f6d2 \u041f\u0440\u0438\u0434\u0431\u0430\u0442\u0438 \u043a\u043e\u0442\u0443\u0448\u043a\u0443", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="\U0001f4cd \u0414\u0435 \u043d\u0430\u0448 \u0441\u0442\u0435\u043d\u0434?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="\U0001f4f8 \u0413\u0430\u043b\u0435\u0440\u0435\u044f \u0440\u043e\u0431\u0456\u0442", callback_data="gallery"))
    builder.row(InlineKeyboardButton(text="\U0001f4c7 \u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u043a\u043e\u043d\u0442\u0430\u043a\u0442 DRUKAR", callback_data="get_vcard"))
    builder.row(InlineKeyboardButton(text="\U0001f4f8 \u041d\u0430\u0434\u0456\u0441\u043b\u0430\u0442\u0438 \u0432\u0456\u0437\u0438\u0442\u043a\u0443 (AI)", callback_data="scan_card"))
    builder.row(InlineKeyboardButton(text="\u270d\ufe0f \u0412\u0432\u0435\u0441\u0442\u0438 \u043a\u043e\u043d\u0442\u0430\u043a\u0442 \u0432\u0440\u0443\u0447\u043d\u0443", callback_data="manual_contact"))
    return builder.as_markup()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "\u0412\u0456\u0442\u0430\u0454\u043c\u043e \u043d\u0430 \u0441\u0442\u0435\u043d\u0434\u0456 *DRUKAR*! \U0001f1fa\U0001f1e6\n\n"
        "\u041c\u0438 \u2014 \u0443\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0438\u0439 \u0432\u0438\u0440\u043e\u0431\u043d\u0438\u043a \u043c\u0430\u0442\u0435\u0440\u0456\u0430\u043b\u0456\u0432 \u0434\u043b\u044f 3D-\u0434\u0440\u0443\u043a\u0443.\n"
        "\u0421\u043f\u0435\u0446\u0456\u0430\u043b\u0456\u0437\u0443\u0454\u043c\u043e\u0441\u044c \u043d\u0430 \u043e\u043f\u0442\u043e\u0432\u0438\u0445 \u043f\u043e\u0441\u0442\u0430\u0447\u0430\u043d\u043d\u044f\u0445 \u0442\u0430 \u044f\u043a\u043e\u0441\u0442\u0456 \u0434\u043b\u044f \u043f\u0440\u043e\u0444\u0435\u0441\u0456\u043e\u043d\u0430\u043b\u0456\u0432.\n\n"
        "\U0001f4f8 *\u041d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0444\u043e\u0442\u043e \u0432\u0456\u0437\u0438\u0442\u043a\u0438* \u2014 \u044f \u043c\u0438\u0442\u0442\u0454\u0432\u043e \u0440\u043e\u0437\u043f\u0456\u0437\u043d\u0430\u044e \u0457\u0457 \u0437\u0430 \u0434\u043e\u043f\u043e\u043c\u043e\u0433\u043e\u044e \u0428\u0406!\n"
        f"\u2709\ufe0f \u0410\u0431\u043e \u043f\u0438\u0448\u0456\u0442\u044c \u043d\u0430\u043c: {CONTACT_EMAIL}",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "scan_card")
async def ask_for_card(callback: types.CallbackQuery):
    await callback.message.answer(
        "\U0001f4f8 \u041d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u0444\u043e\u0442\u043e \u0432\u0456\u0437\u0438\u0442\u043a\u0438. "
        "\u042f \u0440\u043e\u0437\u043f\u0456\u0437\u043d\u0430\u044e \u0456\u043c'\u044f, \u043a\u043e\u043c\u043f\u0430\u043d\u0456\u044e, \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0438 \u0442\u0430 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u043d\u043e \u0441\u0442\u0432\u043e\u0440\u044e \u0443\u0433\u043e\u0434\u0443 \u0432 CRM!"
    )
    await callback.answer()


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not OPENAI_KEY:
        return await message.answer("\u26a0\ufe0f \u041f\u043e\u043c\u0438\u043b\u043a\u0430: OpenAI \u043a\u043b\u044e\u0447 \u043d\u0435 \u043d\u0430\u043b\u0430\u0448\u0442\u043e\u0432\u0430\u043d\u0438\u0439.")
    status_msg = await message.answer("\U0001f50d \u0410\u043d\u0430\u043b\u0456\u0437\u0443\u044e \u0432\u0456\u0437\u0438\u0442\u043a\u0443...")
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    prompt = (
        "You are a business card expert. Extract ALL data: name, company, position, phones, emails, websites, social media. "
        "Reply in Ukrainian. At the end add a JSON block:\n"
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
            try: contact = json.loads(json_match.group(1))
            except: pass
            display_text = full_text[:json_match.start()].strip()
        else:
            display_text = full_text
        await status_msg.edit_text(
            f"\u2705 *\u0414\u0430\u043d\u0456 \u0432\u0456\u0437\u0438\u0442\u043a\u0438:*\n\n{display_text}\n\n\u23f3 \u0417\u0431\u0435\u0440\u0456\u0433\u0430\u044e...",
            parse_mode="Markdown"
        )
        b24_ok, sheets_ok = await asyncio.gather(
            create_b24_deal(contact, source_type="photo"),
            save_to_sheets(contact, source_type="photo")
        )
        parts = []
        if b24_ok: parts.append("\u2705 Bitrix24")
        if sheets_ok: parts.append("\u2705 Google Sheets")
        await message.answer(f"\u0417\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043e: {', '.join(parts)}" if parts else "\u26a0\ufe0f \u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u043d\u043e.")
    except Exception as e:
        logging.error(f"AI Error: {e}")
        await status_msg.edit_text("\u274c \u0421\u043a\u043b\u0430\u0434\u043d\u0430 \u0432\u0456\u0437\u0438\u0442\u043a\u0430! \u0421\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0441\u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0443\u0432\u0430\u0442\u0438 \u0431\u043b\u0438\u0436\u0447\u0435.")


@dp.message(Command("manual_contact"))
@dp.callback_query(F.data == "manual_contact")
async def start_manual_vcard(event, state: FSMContext):
    message = event if isinstance(event, types.Message) else event.message
    await state.clear()
    await state.set_state(ManualVCard.name)
    await message.answer(
        "\u270d\ufe0f *\u0420\u0443\u0447\u043d\u0438\u0439 \u0432\u0432\u0456\u0434 \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u0443*\n\n"
        "\u0412\u0432\u0435\u0434\u0456\u0442\u044c *\u0456\u043c'\u044f \u0442\u0430 \u043f\u0440\u0456\u0437\u0432\u0438\u0449\u0435*:\n_(\u0430\u0431\u043e - \u0449\u043e\u0431 \u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u0438)_",
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery): await event.answer()


@dp.message(ManualVCard.name)
async def vcard_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text if message.text != "-" else "")
    await state.set_state(ManualVCard.company)
    await message.answer("\U0001f3e2 *\u041d\u0430\u0437\u0432\u0430 \u043a\u043e\u043c\u043f\u0430\u043d\u0456\u0457:*", parse_mode="Markdown")

@dp.message(ManualVCard.company)
async def vcard_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text if message.text != "-" else "")
    await state.set_state(ManualVCard.position)
    await message.answer("\U0001f4bc *\u041f\u043e\u0441\u0430\u0434\u0430:*", parse_mode="Markdown")

@dp.message(ManualVCard.position)
async def vcard_position(message: types.Message, state: FSMContext):
    await state.update_data(position=message.text if message.text != "-" else "")
    await state.set_state(ManualVCard.phone)
    await message.answer("\U0001f4de *\u0422\u0435\u043b\u0435\u0444\u043e\u043d:*", parse_mode="Markdown")

@dp.message(ManualVCard.phone)
async def vcard_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text if message.text != "-" else "")
    await state.set_state(ManualVCard.email)
    await message.answer("\u2709\ufe0f *Email:*", parse_mode="Markdown")

@dp.message(ManualVCard.email)
async def vcard_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text if message.text != "-" else "")
    await state.set_state(ManualVCard.website)
    await message.answer("\U0001f310 *\u0421\u0430\u0439\u0442 / \u0441\u043e\u0446\u043c\u0435\u0440\u0435\u0436\u0456:*", parse_mode="Markdown")

@dp.message(ManualVCard.website)
async def vcard_website(message: types.Message, state: FSMContext):
    await state.update_data(website=message.text if message.text != "-" else "")
    await state.set_state(ManualVCard.notes)
    await message.answer("\U0001f4dd *\u041f\u0440\u0438\u043c\u0456\u0442\u043a\u0438:*\n_(\u0430\u0431\u043e - \u0449\u043e\u0431 \u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u0438)_", parse_mode="Markdown")

@dp.message(ManualVCard.notes)
async def vcard_notes(message: types.Message, state: FSMContext):
    await state.update_data(notes=message.text if message.text != "-" else "")
    data = await state.get_data()
    await state.clear()
    summary = (
        f"\U0001f4cb *\u041f\u0456\u0434\u0441\u0443\u043c\u043e\u043a:*\n\n"
        f"\U0001f464 {data.get('name') or '-'}\n"
        f"\U0001f3e2 {data.get('company') or '-'}\n"
        f"\U0001f4bc {data.get('position') or '-'}\n"
        f"\U0001f4de {data.get('phone') or '-'}\n"
        f"\u2709\ufe0f {data.get('email') or '-'}\n"
        f"\U0001f310 {data.get('website') or '-'}\n"
        f"\U0001f4dd {data.get('notes') or '-'}\n\n"
        f"\u23f3 \u0417\u0431\u0435\u0440\u0456\u0433\u0430\u044e..."
    )
    await message.answer(summary, parse_mode="Markdown")
    b24_ok, sheets_ok = await asyncio.gather(
        create_b24_deal(data, source_type="manual"),
        save_to_sheets(data, source_type="manual")
    )
    parts = []
    if b24_ok: parts.append("\u2705 Bitrix24")
    if sheets_ok: parts.append("\u2705 Google Sheets")
    if parts:
        await message.answer(f"\u0417\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043e: {', '.join(parts)}", reply_markup=get_main_menu())
    else:
        await message.answer(f"\u26a0\ufe0f \u041d\u0435 \u0432\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0431\u0435\u0440\u0435\u0433\u0442\u0438. Email: {CONTACT_EMAIL}", reply_markup=get_main_menu())


@dp.message(Command("vcard"))
@dp.callback_query(F.data == "get_vcard")
async def send_vcard(event):
    message = event if isinstance(event, types.Message) else event.message
    vcard_data = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:DRUKAR 3D \u041c\u0430\u0442\u0435\u0440\u0456\u0430\u043b\u0438\nORG:DRUKAR\n"
        "TITLE:\u0412\u0438\u0440\u043e\u0431\u043d\u0438\u043a \u0444\u0456\u043b\u0430\u043c\u0435\u043d\u0442\u0443\nTEL;TYPE=WORK,VOICE:+380673053060\n"
        f"EMAIL:{CONTACT_EMAIL}\nURL:{SITE_URL}\n"
        f"NOTE:{STAND_INFO} | {EXPO_NAME}\nEND:VCARD"
    )
    await message.answer_contact(phone_number="+380673053060", first_name="DRUKAR", last_name="\u041c\u0430\u0442\u0435\u0440\u0456\u0430\u043b\u0438", vcard=vcard_data)
    await message.answer(
        f"\U0001f446 \u041d\u0430\u0442\u0438\u0441\u043d\u0456\u0442\u044c \u043d\u0430 \u043a\u0430\u0440\u0442\u043a\u0443 \u0449\u043e\u0431 \u0437\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u043a\u043e\u043d\u0442\u0430\u043a\u0442\n\n"
        f"\u2709\ufe0f {CONTACT_EMAIL}\n\U0001f310 {SITE_URL}\n\U0001f4cd {STAND_INFO}",
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery): await event.answer()


@dp.message(Command("buy"))
@dp.callback_query(F.data == "buy_filament")
async def cmd_buy(event):
    message = event if isinstance(event, types.Message) else event.message

    display_count = await get_and_increment_counter()

    pay_builder = InlineKeyboardBuilder()
    pay_builder.row(InlineKeyboardButton(
        text="\U0001f4b3  \u041e\u041f\u041b\u0410\u0422\u0418\u0422\u0418 800 \u0433\u0440\u043d  \u2014  \u043e\u0442\u0440\u0438\u043c\u0430\u0442\u0438 \u043a\u043e\u0442\u0443\u0448\u043a\u0443  \u2192",
        url=PAY_URL
    ))

    await message.answer(
        "\U0001f4b3 *\u041d\u0430\u0442\u0438\u0441\u043d\u0456\u0442\u044c \u0449\u043e\u0431 \u043e\u043f\u043b\u0430\u0442\u0438\u0442\u0438 800 \u0433\u0440\u043d \u0456 \u043e\u0442\u0440\u0438\u043c\u0430\u0442\u0438 \u043a\u043e\u0442\u0443\u0448\u043a\u0443:*",
        parse_mode="Markdown",
        reply_markup=pay_builder.as_markup()
    )

    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}qr_payment2.png",
        caption=(
            "\U0001f525 *\u0425\u0456\u0442 \u0432\u0438\u0441\u0442\u0430\u0432\u043a\u0438!*\n"
            f"\u0426\u044e \u043a\u043e\u0442\u0443\u0448\u043a\u0443 \u0441\u044c\u043e\u0433\u043e\u0434\u043d\u0456 \u043e\u0431\u0440\u0430\u043b\u0438 \u0432\u0436\u0435 *{display_count}* \u043b\u044e\u0434\u0435\u0439.\n\n"
            "\u0410\u0431\u043e \u0432\u0456\u0434\u0441\u043a\u0430\u043d\u0443\u0439\u0442\u0435 QR \u043a\u043e\u0434 \u0432\u0438\u0449\u0435.\n"
            f"\u041f\u0456\u0441\u043b\u044f \u043e\u043f\u043b\u0430\u0442\u0438 \u2014 \u043d\u0430\u0434\u0456\u0448\u043b\u0456\u0442\u044c \u043a\u0432\u0438\u0442\u0430\u043d\u0446\u0456\u044e \u0432 \u0446\u0435\u0439 \u0447\u0430\u0442.\n\n"
            f"\U0001f4cd {STAND_INFO}\n\u2709\ufe0f {CONTACT_EMAIL}"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery): await event.answer()


@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    await message.answer_photo(
        photo=f"{GITHUB_BASE_URL}event_preview.jpg",
        caption=(
            f"\U0001f4cd *DRUKAR \u043d\u0430 {EXPO_NAME}*\n\n"
            f"\U0001f3e2 \u041a\u0438\u0457\u0432, \u041c\u0412\u0426 (\u0411\u0440\u043e\u0432\u0430\u0440\u0441\u044c\u043a\u0438\u0439 \u043f\u0440-\u0442, 15)\n"
            f"\u2705 {STAND_INFO}\n\n"
            f"\u2709\ufe0f {CONTACT_EMAIL}\n"
            f"\U0001f517 [\u041e\u0444\u0456\u0446\u0456\u0439\u043d\u0438\u0439 \u0441\u0430\u0439\u0442 \u0432\u0438\u0441\u0442\u0430\u0432\u043a\u0438](https://www.iec-expo.com.ua/addit-2026.html)"
        ),
        parse_mode="Markdown"
    )
    if isinstance(event, types.CallbackQuery): await event.answer()


@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("\U0001f4f8 \u0417\u0430\u0432\u0430\u043d\u0442\u0430\u0436\u0443\u044e \u0433\u0430\u043b\u0435\u0440\u0435\u044e...")
    album = [InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    try:
        await callback.message.answer_media_group(media=album)
    except Exception:
        await callback.message.answer("\u26a0\ufe0f \u0421\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0447\u0435\u0440\u0435\u0437 \u043a\u0456\u043b\u044c\u043a\u0430 \u0441\u0435\u043a\u0443\u043d\u0434.")
    await callback.answer()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_main_menu(bot)
    logging.info("DRUKAR Bot started!")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
