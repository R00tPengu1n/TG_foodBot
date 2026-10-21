import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BotCommand,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.formatting import Bold, as_list, as_marked_section

from recipes_handler import router as recipes_router
from token_data import TOKEN

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

COMMANDS_BUTTON = "Команды"
DESCRIPTION_BUTTON = "Описание бота"

BOT_DESCRIPTION = (
    "Я бот-повар. Подберу случайные рецепты из выбранной категории блюд "
    "и покажу их на русском языке вместе со списком ингредиентов."
)
BOT_SHORT_DESCRIPTION = "Случайные рецепты по категориям блюд."

BOT_COMMANDS = [
    BotCommand(command="start", description="Начать работу с ботом"),
    BotCommand(
        command="category_search_random",
        description="Случайные рецепты, например: /category_search_random 3",
    ),
    BotCommand(command="cancel", description="Отменить поиск"),
]

dp = Dispatcher()
dp.include_router(recipes_router)


@dp.startup()
async def on_startup(bot: Bot) -> None:
    try:
        await bot.set_my_commands(BOT_COMMANDS)
        await bot.set_my_description(BOT_DESCRIPTION)
        await bot.set_my_short_description(BOT_SHORT_DESCRIPTION)
    except TelegramAPIError as error:
        logger.warning("Не удалось обновить профиль бота: %s", error)


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()

    name = message.from_user.full_name if message.from_user else "друг"

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=COMMANDS_BUTTON),
                KeyboardButton(text=DESCRIPTION_BUTTON),
            ]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        f"Привет, {name}! Я бот-повар. С чего начнём?",
        reply_markup=keyboard,
    )


@dp.message(F.text == COMMANDS_BUTTON)
async def show_commands(message: Message) -> None:
    content = as_list(
        as_marked_section(
            Bold("Команды:"),
            *(
                f"/{command.command} — {command.description}"
                for command in BOT_COMMANDS
            ),
            marker="✅ ",
        )
    )
    await message.answer(**content.as_kwargs())


@dp.message(F.text == DESCRIPTION_BUTTON)
async def show_description(message: Message) -> None:
    await message.answer(BOT_DESCRIPTION)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    bot = Bot(token=TOKEN)
    logger.info("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")