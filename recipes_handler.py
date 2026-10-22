import logging
import random
from itertools import batched

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.formatting import Bold, Text
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from mealdb_api import MealDBClient, MealDBError
from translation import translate_texts

logger = logging.getLogger(__name__)

router = Router()

MAX_RECIPES = 10
CATEGORY_BUTTONS_IN_ROW = 5
SHOW_RECIPES_BUTTON = "Покажи рецепты"
MAX_INGREDIENTS = 20
TEXTS_PER_MEAL = 3
INSTRUCTIONS_CHUNK_SIZE = 3000

SERVICE_UNAVAILABLE_TEXT = "Сервис рецептов сейчас недоступен. Попробуйте позже."


class RecipeStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_recipes = State()


def parse_recipes_count(args: str | None) -> int:
    if args is None:
        raise ValueError(
            "Укажите количество рецептов.\n"
            "Пример: /category_search_random 3"
        )

    try:
        count = int(args)
    except ValueError:
        raise ValueError(
            "Количество рецептов должно быть целым числом."
        ) from None

    if not 1 <= count <= MAX_RECIPES:
        raise ValueError(
            f"Количество рецептов должно быть от 1 до {MAX_RECIPES}."
        )

    return count


def get_ingredients(meal: dict) -> list[str]:
    ingredients = []

    for number in range(1, MAX_INGREDIENTS + 1):
        name = (meal.get(f"strIngredient{number}") or "").strip()
        measure = (meal.get(f"strMeasure{number}") or "").strip()

        if not name:
            continue

        ingredients.append(f"{name} ({measure})" if measure else name)

    return ingredients


def split_text(text: str, max_length: int) -> list[str]:
    chunks = []
    current = ""

    for line in text.splitlines(keepends=True):
        if current and len(current) + len(line) > max_length:
            chunks.append(current)
            current = ""

        while len(line) > max_length:
            chunks.append(line[:max_length])
            line = line[max_length:]

        current += line

    if current:
        chunks.append(current)

    return chunks or [""]


def build_recipe_messages(
    title: str,
    instructions: str,
    ingredients: str,
) -> list[Text]:
    chunks = split_text(instructions, INSTRUCTIONS_CHUNK_SIZE)
    messages = []

    for index, chunk in enumerate(chunks):
        parts = []

        if index == 0:
            parts.extend([Bold(title), "\n\n", Bold("Рецепт:"), "\n"])

        parts.append(chunk)

        if index == len(chunks) - 1:
            parts.extend(["\n\n", Bold("Ингредиенты:"), " ", ingredients])

        messages.append(Text(*parts))

    return messages


@router.message(Command("cancel"))
async def cancel_search(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Сейчас нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "Поиск отменён.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("category_search_random"))
async def start_category_search(
    message: Message,
    command: CommandObject,
    state: FSMContext,
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
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return

    if not categories:
        await message.answer("Не удалось получить список категорий.")
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
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(RecipeStates.waiting_for_category)


@router.message(RecipeStates.waiting_for_category)
async def choose_random_recipes(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    category = message.text

    if not category or category not in data.get("categories", []):
        await message.answer(
            "Пожалуйста, выберите категорию кнопкой ниже "
            "или отправьте /cancel, чтобы отменить поиск."
        )
        return

    try:
        async with MealDBClient() as api:
            meals = await api.get_meals_by_category(category)
    except MealDBError:
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return

    if not meals:
        await message.answer(
            "В этой категории пока нет рецептов. Выберите другую."
        )
        return

    recipes_count = min(data["recipes_count"], len(meals))
    selected_meals = random.sample(meals, k=recipes_count)
    meal_ids = [meal["idMeal"] for meal in selected_meals]
    await state.update_data(meal_ids=meal_ids)

    titles = await translate_texts(
        [meal["strMeal"] for meal in selected_meals]
    )

    builder = ReplyKeyboardBuilder()
    builder.button(text=SHOW_RECIPES_BUTTON)

    await message.answer(
        f"Как Вам такие варианты: {', '.join(titles)}",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(RecipeStates.waiting_for_recipes)


@router.message(
    RecipeStates.waiting_for_recipes,
    F.text == SHOW_RECIPES_BUTTON,
)
async def show_recipes(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    meal_ids = data.get("meal_ids", [])
    await state.clear()

    if not meal_ids:
        await message.answer(
            "Не удалось найти выбранные рецепты. Начните поиск заново.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await message.answer(
        "Загружаю рецепты...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        async with MealDBClient() as api:
            meals = await api.get_meals_by_ids(meal_ids)
    except MealDBError:
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return

    if not meals:
        await message.answer(
            "Не удалось загрузить рецепты. Начните поиск заново."
        )
        return

    logger.info("Загружено рецептов: %d из %d", len(meals), len(meal_ids))

    texts = []
    for meal in meals:
        texts.extend(
            (
                meal["strMeal"],
                meal.get("strInstructions") or "",
                ", ".join(get_ingredients(meal)),
            )
        )

    translated = await translate_texts(texts)

    for title, instructions, ingredients in batched(
        translated, TEXTS_PER_MEAL
    ):
        for content in build_recipe_messages(
            title, instructions, ingredients
        ):
            await message.answer(**content.as_kwargs())


@router.message(RecipeStates.waiting_for_recipes)
async def remind_show_recipes(message: Message) -> None:
    await message.answer(
        f"Нажмите кнопку «{SHOW_RECIPES_BUTTON}», чтобы увидеть рецепты, "
        "или /cancel, чтобы отменить поиск."
    )