import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from mealdb_api import MealDBClient, MealDBError

logger = logging.getLogger(__name__)

router = Router()

MAX_RECIPES = 10
CATEGORY_BUTTONS_IN_ROW = 5

class RecipeStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_recipes = State()

def parse_recipes_count(args: str | None) -> int:
    if args is None:
        raise ValueError(
            "Укажите количество рецептов. \n"
            "Пример: /category_search_random 3"
        )
    try:
        count = int(args)
    except ValueError:
        raise ValueError(
            "Количество рецептов должно быть целым числом"
        ) from None

    if not 1 <= count <= MAX_RECIPES:
        raise ValueError(
            f"Количество рецептов должно быть от 1 до {MAX_RECIPES}"
        )

    return count

@router.message(Command("category_search_random"))
async def start_category_search(
        message: Message,
        command: CommandObject,
        state: FSMContext
) -> None:
    try:
        recipes_count = parse_recipes_count(command.args)
    except ValueError as error:
        await message.answer(str(error))
        return

    try:
        async with MealDBClient() as api:
            categories = await api.get_categories()

    except MealDBError:
        await message.answer(
            "Сервис рецептов сейчас недоступен. Попробуйте позже"
        )
        return

    await state.set_data(
        {"recipes_count": recipes_count, "categories": categories}
    )

    builder = ReplyKeyboardBuilder()
    for category in categories:
        builder.button(text=category)
    builder.adjust(CATEGORY_BUTTONS_IN_ROW)

    await message.answer(
        "Выберите категорию:",
        reply_markup=builder.as_markup(resize_keyboard = True)
    )
    await state.set_state(RecipeStates.waiting_for_category)








