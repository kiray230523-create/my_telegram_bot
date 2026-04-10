import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import uuid
import os

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8709089116:AAHaudfsi29YisCze9Kq2YZXnGYyxCgU7B8" # ← ЗАМЕНИТЕ НА ВАШ ТОКЕН
ADMIN_IDS = [2140279307] # ← ЗАМЕНИТЕ НА ВАШ TELEGRAM ID

# ==================== БАЗА ДАННЫХ ====================
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    channel TEXT,
    ad_type TEXT,
    duration INTEGER,
    date TEXT,
    time TEXT,
    total_price INTEGER,
    payment_id TEXT,
    status TEXT,
    post_text TEXT,
    post_media TEXT,
    created_at TEXT
)
""")
conn.commit()

# ==================== СОСТОЯНИЯ FSM ====================
class BookingState(StatesGroup):
    choosing_channel = State()
    choosing_ad_type = State()
    choosing_duration = State()
    choosing_date = State()
    choosing_time = State()
    waiting_payment = State()
    waiting_post_text = State()
    waiting_post_media = State()

# ==================== КАНАЛЫ ====================
CHANNELS = {
    "1": "Скидочный Навигатор",
    "2": "Мужской Кэшбэк",
    "3": "Кэшбэк Гуру",
    "4": "Детский",
    "5": "ЛедиShop",
    "6": "Кэшбэк-маркет"
}

AD_TYPES = {
    "1": "Товар с раздачей",
    "2": "Реклама товара",
    "3": "Реклама кэшбэк-каналов",
    "4": "Реклама ТГ-каналов"
}

# Цены для товара с раздачей
PRICES_GIVEAWAY = {
    "Скидочный Навигатор": {"1": 150, "3": 400, "7": 700},
    "Мужской Кэшбэк": {"1": 150, "3": 400, "7": 700},
    "Кэшбэк Гуру": {"1": 150, "3": 400, "7": 700},
    "Детский": {"1": 100, "3": 250, "7": 500},
    "ЛедиShop": {"1": 100, "3": 250, "7": 500},
    "Кэшбэк-маркет": {"1": 100, "3": 250, "7": 500}
}

# Цены для рекламы товара
PRICES_PRODUCT = {
    "Скидочный Навигатор": {"1": 200, "3": 500, "7": 1000},
    "Мужской Кэшбэк": {"1": 200, "3": 500, "7": 1000},
    "Кэшбэк Гуру": {"1": 200, "3": 500, "7": 1000},
    "Детский": {"1": 100, "3": 400, "7": 1000},
    "ЛедиShop": {"1": 150, "3": 400, "7": 700},
    "Кэшбэк-маркет": {"1": 150, "3": 400, "7": 700}
}

# ==================== КЛАВИАТУРЫ ====================
def get_channels_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for key, name in CHANNELS.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=name, callback_data=f"channel_{key}")])
    return kb

def get_ad_types_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for key, name in AD_TYPES.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=name, callback_data=f"adtype_{key}")])
    return kb

def get_duration_kb(ad_type):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if ad_type in ["Товар с раздачей", "Реклама товара"]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="1 день", callback_data="dur_1"),
            InlineKeyboardButton(text="3 дня", callback_data="dur_3"),
            InlineKeyboardButton(text="7 дней", callback_data="dur_7")
        ])
    else:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="24 часа", callback_data="dur_24"),
            InlineKeyboardButton(text="48 часов", callback_data="dur_48")
        ])
    return kb

def get_time_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    times = ["07:30", "08:30", "09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30", "16:30", "17:30", "18:30", "19:30", "20:30", "21:30", "22:30"]
    row = []
    for t in times:
        row.append(InlineKeyboardButton(text=t, callback_data=f"time_{t}"))
        if len(row) == 4:
            kb.inline_keyboard.append(row)
            row = []
    if row:
        kb.inline_keyboard.append(row)
    return kb

# ==================== БОТ ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🎯 Добро пожаловать в сервис размещения рекламы!\n\nВыберите канал:", reply_markup=get_channels_kb())
    await state.set_state(BookingState.choosing_channel)

@dp.callback_query(F.data.startswith("channel_"), BookingState.choosing_channel)
async def channel_selected(callback: types.CallbackQuery, state: FSMContext):
    channel_key = callback.data.split("_")[1]
    channel_name = CHANNELS[channel_key]
    await state.update_data(channel=channel_name)
    await callback.message.edit_text(f"📢 Выбран канал: {channel_name}\n\nТеперь выберите тип размещения:", reply_markup=get_ad_types_kb())
    await state.set_state(BookingState.choosing_ad_type)
    await callback.answer()

@dp.callback_query(F.data.startswith("adtype_"), BookingState.choosing_ad_type)
async def adtype_selected(callback: types.CallbackQuery, state: FSMContext):
    adtype_key = callback.data.split("_")[1]
    adtype_name = AD_TYPES[adtype_key]
    await state.update_data(ad_type=adtype_name)
    await callback.message.edit_text(f"📢 Тип: {adtype_name}\n\nВыберите период размещения:", reply_markup=get_duration_kb(adtype_name))
    await state.set_state(BookingState.choosing_duration)
    await callback.answer()

@dp.callback_query(F.data.startswith("dur_"), BookingState.choosing_duration)
async def duration_selected(callback: types.CallbackQuery, state: FSMContext):
    duration = int(callback.data.split("_")[1])
    await state.update_data(duration=duration)
    await callback.message.edit_text("📅 Введите дату публикации в формате ДД.ММ.ГГГГ\n(например, 15.04.2026)")
    await state.set_state(BookingState.choosing_date)
    await callback.answer()

@dp.message(BookingState.choosing_date)
async def date_selected(message: types.Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        if date < datetime.now():
            await message.answer("❌ Дата не может быть в прошлом. Введите будущую дату.")
            return
        await state.update_data(date=message.text.strip())
        await message.answer("⏰ Выберите время публикации:", reply_markup=get_time_kb())
        await state.set_state(BookingState.choosing_time)
    except ValueError:
        await message.answer("❌ Неверный формат. Введите дату в формате ДД.ММ.ГГГГ")

@dp.callback_query(F.data.startswith("time_"), BookingState.choosing_time)
async def time_selected(callback: types.CallbackQuery, state: FSMContext):
    time = callback.data.split("_")[1]
    data = await state.get_data()
    channel = data["channel"]
    ad_type = data["ad_type"]
    duration = data["duration"]
    
    # Расчёт цены
    if ad_type == "Товар с раздачей":
        price = PRICES_GIVEAWAY[channel][str(duration)]
    elif ad_type == "Реклама товара":
        price = PRICES_PRODUCT[channel][str(duration)]
    else:
        price = 500
    
    total_price = price
    await state.update_data(time=time, total_price=total_price)
    
    await callback.message.edit_text(
        f"💰 Стоимость: {total_price} руб.\n\n"
        f"📌 Канал: {channel}\n"
        f"📌 Тип: {ad_type}\n"
        f"📌 Период: {duration} дня/дней\n"
        f"📌 Дата: {data['date']}\n"
        f"📌 Время: {time}\n\n"
        f"Для подтверждения заказа отправьте /confirm"
    )
    await state.set_state(BookingState.waiting_payment)
    await callback.answer()

@dp.message(Command("confirm"), BookingState.waiting_payment)
async def confirm_payment(message: types.Message, state: FSMContext):
    await message.answer("✅ Заказ подтверждён! Теперь отправьте текст вашего поста.")
    await state.set_state(BookingState.waiting_post_text)

@dp.message(BookingState.waiting_post_text)
async def post_text_received(message: types.Message, state: FSMContext):
    await state.update_data(post_text=message.text)
    await message.answer("🖼 Теперь отправьте фото или видео (или нажмите /skip, чтобы пропустить)")
    await state.set_state(BookingState.waiting_post_media)

@dp.message(Command("skip"), BookingState.waiting_post_media)
async def skip_media(message: types.Message, state: FSMContext):
    await state.update_data(post_media="")
    await save_order(message, state)

@dp.message(BookingState.waiting_post_media, F.photo | F.video)
async def post_media_received(message: types.Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    else:
        await message.answer("❌ Пожалуйста, отправьте фото или видео (или /skip)")
        return
    
    await state.update_data(post_media=file_id)
    await save_order(message, state)

async def save_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    cursor.execute("""
        INSERT INTO orders (user_id, channel, ad_type, duration, date, time, total_price, payment_id, status, post_text, post_media, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message.from_user.id, data["channel"], data["ad_type"], data["duration"],
        data["date"], data["time"], data["total_price"], "", "pending",
        data["post_text"], data.get("post_media", ""), datetime.now().isoformat()
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    # Уведомление админу
    admin_text = (
        f"🔔 НОВАЯ ЗАЯВКА #{order_id}\n\n"
        f"Пользователь: @{message.from_user.username or message.from_user.id}\n"
        f"Канал: {data['channel']}\n"
        f"Тип: {data['ad_type']}\n"
        f"Период: {data['duration']} дня/дней\n"
        f"Дата: {data['date']}\n"
        f"Время: {data['time']}\n"
        f"Сумма: {data['total_price']} руб.\n\n"
        f"Текст поста:\n{data['post_text']}\n"
    )
    
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, admin_text)
        if data.get("post_media"):
            await bot.send_photo(admin_id, data["post_media"])
    
    await message.answer("✅ Ваша заявка отправлена администратору. Ожидайте подтверждения.")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())