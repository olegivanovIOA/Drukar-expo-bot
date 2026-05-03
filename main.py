# --- ОБНОВЛЕННЫЕ ОБРАБОТЧИКИ ---

@dp.message(Command("find_us"))
@dp.callback_query(F.data == "find_us")
async def find_us(event):
    message = event if isinstance(event, types.Message) else event.message
    
    # Ссылка на картинку-анонс из вашего сообщения
    photo_url = GITHUB_BASE_URL + "event_preview.jpg" # Переименуйте фото участника в это имя на GitHub
    
    caption_text = (
        "📍 **DRUKAR на Addit EXPO 3D-2026**\n\n"
        "📅 26-28 мая 2026 года\n"
        "🏢 Киев, МВЦ (Броварской пр-т, 15)\n"
        "✅ Наш стенд: **A-45 (Павильон №2)**\n\n"
        "Официальная страница мероприятия:\n"
        "🔗 https://www.iec-expo.com.ua/addit-2026.html"
    )
    
    try:
        # Пытаемся отправить фото. Если ссылка битая, отправим просто текст.
        await message.answer_photo(
            photo=photo_url,
            caption=caption_text,
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer(caption_text, disable_web_page_preview=False)
        
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@dp.message(Command("buy"))
@dp.callback_query(F.data == "buy_filament")
async def cmd_buy(event):
    message = event if isinstance(event, types.Message) else event.message
    qr_url = GITHUB_BASE_URL + "qr_payment.png"
    
    caption_text = (
        "🛒 **Оплата катушки (ФОП)**\n\n"
        "1. Отсканируйте QR-код для перехода к оплате.\n"
        "2. Введите сумму и подтвердите платеж.\n"
        "3. **Важно:** Пришлите скриншот квитанции в этот чат для подтверждения заказа.\n\n"
        "Спасибо, что выбираете Drukar! 🇺🇦"
    )
    
    try:
        await message.answer_photo(
            photo=qr_url,
            caption=caption_text,
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer(
            "⚠️ Не удалось загрузить QR-код. Пожалуйста, используйте прямую ссылку на оплату или обратитесь к менеджеру.\n\n" + caption_text
        )

    if isinstance(event, types.CallbackQuery):
        await event.answer()

# --- МЕНЮ КОМАНД (BOTFATHER / INTERFACE) ---
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Главное меню 🚀"),
        BotCommand(command="/find_us", description="Где наш стенд? 📍"),
        BotCommand(command="/buy", description="Купить катушку 🛒"),
        BotCommand(command="/gallery", description="Галерея работ 📸"),
    ]
    await bot.set_my_commands(main_menu_commands)