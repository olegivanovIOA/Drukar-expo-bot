# Базовый URL вашего репозитория (убедитесь, что логин верный)
GITHUB_BASE_URL = "https://raw.githubusercontent.com/olegivanovIOA/Drukar-expo-bot/main/"

def get_main_menu():
    builder = InlineKeyboardBuilder()
    # 2) Сайт
    builder.row(InlineKeyboardButton(text="🌐 Наш сайт", url="https://www.3drukar.com"))
    
    # 3) Calendly для встреч
    builder.row(InlineKeyboardButton(text="📅 Назначить встречу", url="https://calendly.com/ioa4/30min"))
    
    builder.row(InlineKeyboardButton(text="🛒 Купить катушку", url="https://www.3drukar.com/shop"))
    builder.row(InlineKeyboardButton(text="📍 Где наш стенд?", callback_data="find_us"))
    
    # Кнопка для галереи
    builder.row(InlineKeyboardButton(text="💎 Галерея работ (13 фото)", callback_data="gallery"))
    
    return builder.as_markup()

# --- ОБРАБОТЧИК ГАЛЕРЕИ (на 13 файлов) ---
@dp.callback_query(F.data == "gallery")
async def show_gallery(callback: types.CallbackQuery):
    await callback.message.answer("📸 Подготавливаю портфолио работ Drukar...")
    
    # Telegram поддерживает максимум 10 фото в одной группе (media group)
    # Поэтому разобьем 13 фото на два альбома: 10 и 3.
    
    # Первый альбом (1-10)
    album1 = []
    for i in range(1, 11):
        album1.append(types.InputMediaPhoto(
            media=f"{GITHUB_BASE_URL}work{i}.jpg",
            caption=f"Пример работы #{i}" if i == 1 else "" # Описание только у первого фото
        ))
        
    # Второй альбом (11-13)
    album2 = []
    for i in range(11, 14):
        album2.append(types.InputMediaPhoto(
            media=f"{GITHUB_BASE_URL}work{i}.jpg"
        ))

    try:
        await callback.message.answer_media_group(media=album1)
        await asyncio.sleep(1) # Небольшая пауза, чтобы не спамить
        await callback.message.answer_media_group(media=album2)
    except Exception as e:
        await callback.message.answer("⚠️ Не удалось загрузить все фото. Проверьте, что файлы названы work1.jpg ... work13.jpg и лежат в корне GitHub.")
    
    await callback.answer()