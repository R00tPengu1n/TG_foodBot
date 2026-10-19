import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from token_data import TOKEN
from recipes_handler import router

logging.basicConfig(level = logging.INFO)

bot = Bot(token = TOKEN)
dp = Dispatcher()
dp.include_router(router)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f'Привет, {message.from_user.full_name}!\n'
        f'Я - бот повар. Я умею искать рецепты.\n\n'
        f'Введите команду: /category_search_random и число рецептов.\n'
        f'Например: /category_search_random 3'
    )

async def main() -> None:
    print("Бот запущен...")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())