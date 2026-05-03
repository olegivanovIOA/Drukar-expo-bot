# --- ОБНОВЛЕННЫЕ ОБРАБОТЧИКИ ---

@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    # Используем прямую ссылку на фото карты из GitHub
    photo_url = GITHUB_BASE_URL + "map.jpg" 
    
    caption_text = (
        "📍 **Мы в Павильоне №2, стенд A-45.**\n\n"
        "Подробности о выставке Addit EXPO 3D-2026 можно найти на официальном сайте:\n"
        "🔗 https://www.iec-expo.com.ua/addit-2026.html\n\n"
        "Ждем вас на стенде Drukar!"
    )
    
    try:
        await message.answer_photo(
            photo=photo_url,
            caption=caption_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки карты: {e}")
        await message.answer(caption_text, disable_web_page_preview=False)
        
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.message(Command("buy"))
@dp.callback_query(F.data == "buy_filament") # Добавим этот callback в меню если нужно
async def cmd_buy(event):
    message = event if isinstance(event, types.Message) else event.message
    # Загрузите файл qr_payment.png в корень вашего репозитория GitHub
    qr_url = GITHUB_BASE_URL + "qr_payment.png"
    
    caption_text = (
        "🛒 **Оплата заказа через ФОП**\n\n"
        "Для покупки катушки отсканируйте QR-код выше или используйте реквизиты в приложении вашего банка.\n\n"
        "После оплаты, пожалуйста, пришлите скриншот квитанции в этот чат."
    )
    
    try:
        await message.answer_photo(
            photo=qr_url,
            caption=caption_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки QR: {e}")
        await message.answer("⚠️ Изображение QR-кода временно недоступно, обратитесь к администратору.")

    if isinstance(event, types.CallbackQuery):
        await event.answer()

# --- ОБНОВЛЕННОЕ ИНЛАЙН-МЕНЮ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", url="https://calendly.com/ioa4/30min"))
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", callback_data="buy_filament"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    builder.row(InlineKeyboardButton(text="📸 Галерея работ", callback_data="gallery"))
    return builder.as_markup()