import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils import keyboard

from token_data import TOKEN
from recipes_handler import router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level = logging.INFO)

bot = Bot(token = TOKEN)
dp = Dispatcher()
dp.include_router(router)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    keyboard = ReplyKeyboardMarkup(
        keyboard = [
            [KeyboardButton(text = "Найти рецепты")]
        ],
        resize_keyboard = True,
        input_field_placeholder = "Нажми на кнопку..."
    )

    await message.answer(
        f'Привет, {message.from_user.full_name}! \n'
        f'Я - бот повар. Нажми на кнопку ниже, чтобы начать поиск!',
        reply_markup = keyboard
    )

async def main() -> None:
    print("Бот запущен...")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())