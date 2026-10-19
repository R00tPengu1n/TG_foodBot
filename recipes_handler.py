from mailbox import Message

from aiogram import Router, types, F
from aiogram.client.session import aiohttp
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random

from aiogram.types import reply_markup_union
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from googletrans import Translator
from unicodedata import lookup

router = Router()

class RecipeStates(StatesGroup):
    waiting_for_count = State()
    waiting_for_category = State()
    waiting_for_recipes = State()

@router.message(Command("category_search_random"))
async def start_search(message: types.Message, command = CommandObject, state = FSMContext):
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
            "Ошибка: число рецептов. ЧИСЛО"
        )
        return

    await state.update_data(num_recipes = num_recipes)

    await message.answer(
        f'Принято! Ищу {num_recipes} случайных рецептов. Выберите категорию...'
    )

    await state.set_state(RecipeStates.waiting_for_category)

async def show_categories(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    num_recipes = user_data.get('num_recipes', 3)

    categories = []

    try:
        session = aiohttp.ClientSession()
        url = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
        async with session.get(url) as response:
            data = await response.json()


        if data and 'meals' in data:
            for item in data['meals']:
                cat_name = item.get('strCategory')
                if cat_name:
                    categories.append(str(cat_name))
    except Exception as e:

        print(f"ОШИБКА ПРИ ЗАПРОСЕ: {e}")
        await message.answer("Произошла ошибка при связи с API.")
        return

    if not categories:
        await message.answer("Категории не найдены (список пуст).")
        return

    builder = ReplyKeyboardBuilder()
    for category in categories:
        builder.add(types.KeyboardButton(text=category))
        builder.adjust(4)

        await message.answer(
            text=f"Отлично! Ищу {num_recipes} рецептов.\nВыберите категорию:",
            reply_markup=builder.as_markup(resize_keyboard=True)
            )
        await state.set_state(RecipeStates.waiting_for_category)

        await session.close()

@router.message(RecipeStates.waiting_for_count)
async def process_count(message: types.Message, state:FSMContext):
    if not message.text.isdigit():
        await message.answer(
            f'Пожалуйтса, введите целое число (например 3)'
        )
        return

    num_recipes = int(message.text)

    await state.update_data(num_recipes = num_recipes)

    await show_categories(message, state)

@router.message(F.text == "Найти рецепты")
async def ask_for_count(message: types.Message, state: FSMContext):
    await message.answer(
        f'Сколько рецептов ты хочешь найти? Напиши число (например, 3)'
    )
    await state.set_state(RecipeStates.waiting_for_count)

@router.message(RecipeStates.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    category = message.text
    user_data = await state.get_data()
    num_recipes = user_data.get('num_recipes', 3)

    await message.answer(
        f'Ищу рецепты в категории {category}'
    )

    async with aiohttp.ClientSession() as session:
        url = f'https://www.themealdb.com/api/json/v1/1/filter.php?c={category}'
        async with session.get(url) as response:
            data = await response.json()

    if not data.get('meals'):
        await message.answer(
            "В этой категории пока нет рецептов. Выберите другую."
        )
        return

    all_meals = data["meals"]
    k = min(num_recipes, len(all_meals))
    random_meals = random.choices(all_meals, k=k)
    meal_ids = [meal['idMeal'] for meal in random_meals]

    await state.update_data(meal_ids = meal_ids, current_category = category)

    translator = Translator()
    recipe_titles = []

    for meal_id in meal_ids:
        lookup_url = f'https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}'

        async with session.get(lookup_url) as response:
            meal_data = await response.json()
            if meal_data.get('meals'):
                title_en = meal_data['meals'][0]['strMeal']
                try:
                    translated = await translator.translate(title_en, dest = 'ru')
                    recipe_titles.append(
                        f"{translated.text}"
                    )
                except Exception:
                    await message.answer(
                        f'Не удалось перевести рецепт на русский язык'
                    )
                    recipe_titles.append(
                        f'{title_en}'
                    )

        result_text = "Вот что я нашёл:\n\n" + "\n".json(recipe_titles)

    builder = ReplyKeyboardBuilder()

    builder.add(types.KeyboardButton(text = "Покажи рецепты"))

    await message.answer(
        text = result_text,
        reply_markup = builder.as_markup(resize_keyboard = True)
    )

    await state.set_state(RecipeStates.waiting_for_recipes)
