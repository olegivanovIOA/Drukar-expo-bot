GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

def get_main_menu():
    builder = InlineKeyboardBuilder()
    # Новые ссылки
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", url="https://calendly.com/ioa4/30min"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", url="https://www.3drukar.com/shop"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="💎 Галерея работ", callback_data="gallery"))
    return builder.as_markup()

@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Загружаю портфолио (13 фото)...")
    
    # Разбиваем на 2 альбома (10 и 3 фото)
    media1 = [types.InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(1, 11)]
    media2 = [types.InputMediaPhoto(media=f"{GITHUB_BASE_URL}work{i}.jpg") for i in range(11, 14)]
    
    try:
        await callback.message.answer_media_group(media=media1)
        await asyncio.sleep(0.5)
        await callback.message.answer_media_group(media=media2)
    except Exception as e:
        await callback.message.answer("🖼 Фото еще подгружаются на сервер. Попробуйте через минуту!")
    await callback.answer()