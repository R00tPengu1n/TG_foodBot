from mailbox import Message

from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class RecipeStates(StatesGroup):
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

