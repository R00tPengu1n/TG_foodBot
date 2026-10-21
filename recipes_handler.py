import random
from turtledemo.sorting_animate import instructions1

import aiohttp
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from googletrans import Translator


router = Router()

translator = Translator()

class RecipeStates(StatesGroup):
    waiting_for_count = State()
    waiting_for_category = State()
    waiting_for_recipes = State()


CATEGORIES = {
    "Говядина": "Beef",
    "Завтрак": "Breakfast",
    "Курица": "Chicken",
    "Десерты": "Dessert",
    "Козлятина": "Goat",
    "Баранина": "Lamb",
    "Разное": "Miscellaneous",
    "Паста": "Pasta",
    "Свинина": "Pork",
    "Морепродукты": "Seafood",
    "Гарниры": "Side",
    "Закуски": "Starter",
    "Веганские": "Vegan",
    "Вегетарианские": "Vegetarian",
}


@router.message(Command("category_search_random"))
async def start_search(
    message: types.Message,
    command: CommandObject,
    state: FSMContext
):
    if command.args is None:
        await message.answer(
            "Ошибка: вы не указали количество рецептов.\n"
            "Пример: /category_search_random 3"
        )
        return

    try:
        num_recipes = int(command.args)
    except ValueError:
        await message.answer(
            "Ошибка: количество рецептов должно быть целым числом."
        )
        return

    if num_recipes <= 0:
        await message.answer(
            "Количество рецептов должно быть больше нуля."
        )
        return

    await state.update_data(num_recipes=num_recipes)
    await show_categories(message, state)


async def show_categories(
    message: types.Message,
    state: FSMContext
):
    user_data = await state.get_data()
    num_recipes = user_data.get("num_recipes", 3)

    builder = ReplyKeyboardBuilder()

    for category in CATEGORIES:
        builder.add(types.KeyboardButton(text=category))

    builder.adjust(4)

    await message.answer(
        text=(
            f"Отлично! Ищу {num_recipes} рецептов.\n"
            "Выберите категорию:"
        ),
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

    await state.set_state(RecipeStates.waiting_for_category)


@router.message(F.text == "Найти рецепты")
async def ask_for_count(
    message: types.Message,
    state: FSMContext
):
    await message.answer(
        "Сколько рецептов ты хочешь найти?\n"
        "Напиши число, например: 3"
    )

    await state.set_state(RecipeStates.waiting_for_count)


@router.message(RecipeStates.waiting_for_count)
async def process_count(
    message: types.Message,
    state: FSMContext
):
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите целое число.\n"
            "Например: 3"
        )
        return

    num_recipes = int(message.text)

    if num_recipes <= 0:
        await message.answer(
            "Количество рецептов должно быть больше нуля."
        )
        return

    await state.update_data(num_recipes=num_recipes)
    await show_categories(message, state)


@router.message(RecipeStates.waiting_for_category)
async def process_category(
    message: types.Message,
    state: FSMContext
):
    russian_category = message.text

    if russian_category not in CATEGORIES:
        await message.answer(
            "Пожалуйста, выберите категорию кнопкой ниже."
        )
        return

    english_category = CATEGORIES[russian_category]

    user_data = await state.get_data()
    num_recipes = user_data.get("num_recipes", 3)

    await message.answer(
        f"Ищу рецепты в категории «{russian_category}»..."
    )

    url = "https://www.themealdb.com/api/json/v1/1/filter.php"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            params={"c": english_category}
        ) as response:
            data = await response.json()

    if not data.get("meals"):
        await message.answer(
            "В этой категории пока нет рецептов. Выберите другую."
        )
        return

    all_meals = data["meals"]
    k = min(num_recipes, len(all_meals))

    random_meals = random.sample(all_meals, k=k)

    meal_ids = [meal["idMeal"] for meal in random_meals]

    await state.update_data(
        meal_ids=meal_ids,
        current_category=russian_category
    )

    translator = Translator()
    recipe_titles = []

    async with aiohttp.ClientSession() as session:
        for meal_id in meal_ids:
            lookup_url = (
                "https://www.themealdb.com/api/json/v1/1/lookup.php"
            )

            async with session.get(
                lookup_url,
                params={"i": meal_id}
            ) as response:
                meal_data = await response.json()

            if not meal_data.get("meals"):
                continue

            title_en = meal_data["meals"][0]["strMeal"]

            try:
                translated = translator.translate(
                    title_en,
                    dest="ru"
                )
                recipe_titles.append(translated.text)
            except Exception as e:
                print(f"Ошибка перевода: {e}")
                recipe_titles.append(title_en)

    result_text = (
        "Вот что я нашёл:\n\n"
        + "\n".join(
            f"• {title}" for title in recipe_titles
        )
    )

    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Покажи рецепты"))

    await message.answer(
        text=result_text,
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

    await state.set_state(RecipeStates.waiting_for_recipes)


@router.message(
    RecipeStates.waiting_for_recipes,
    F.text == "Покажи рецепты"
)
async def show_recipes(
    message: types.Message,
    state: FSMContext
):
    user_data = await state.get_data()
    meal_ids = user_data.get("meal_ids", [])

    if not meal_ids:
        await message.answer(
            "Не удалось найти сохранённые рецепты. "
            "Попробуйте начать поиск заново."
        )
        await state.clear()
        return

    await message.answer(
        "Секунду, загружаю подробные рецепты..."
    )

    async with aiohttp.ClientSession() as session:
        for meal_id in meal_ids:
            lookup_url = (
                "https://www.themealdb.com/api/json/v1/1/lookup.php"
            )

            async with session.get(
                lookup_url,
                params={"i": meal_id}
            ) as response:
                data = await response.json()

            if not data.get("meals"):
                continue

            meal = data["meals"][0]

            title = meal["strMeal"]
            instructions = meal.get("strInstructions", "")

            try:
                translated_title = translator.translate(
                    title,
                    dest = "ru"
                ).text

                translated_instructions = translator.translate(
                    instructions,
                    dest = "ru"
                ).text

            except Exception as e:
                print("Ошибка перевода: {e}")

                translated_title = title
                translated_instructions = instructions

            ingredients = []

            for i in range(1, 21):
                ingredient = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")

                if ingredient and ingredient.strip():
                    ingredients.append(
                        f"• {ingredient} — {measure or ''}"
                    )

            recipe_text = (
                f"🍽 <b>{translated_title}</b>\n\n"
                f"<b>Ингредиенты:</b>\n"
                f"{chr(10).join(ingredients)}\n\n"
                f"<b>Приготовление:</b>\n"
                f"{translated_instructions}"
            )

            await message.answer(recipe_text)

    await state.clear()