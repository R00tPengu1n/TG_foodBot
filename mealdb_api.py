import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL="https://www.themealdb.com/api/json/v1/1"
REQUEST_TIMEOUT=aiohttp.ClientTimeout(total=10)

class MealDBError(Exception):
    """Ошибка при обращении к API TheMealDB"""

class MealDBClient:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "MealDBClient":
        self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _get_json(self, endpoint: str, params: dict) -> dict:
        if self._session is None:
            raise RuntimeError(
                "Используйте клиент через 'async with MealDBClient() as api:'"
            )

        url = f"{BASE_URL}/{endpoint}"

        try:
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as error:
            logger.error("Ошибка запроса к %s: %s", url, error)
            raise MealDBError(f"Не удалось получить данные: {endpoint}") from error

    async def get_categories(self) -> list[str]:
        data = await self._get_json("list.php", {"c": "list"})
        return [item["strCategory"] for item in data.get("meals") or []]

    async def get_meals_by_category(self, category: str) -> list[dict]:
        data = await self._get_json("filter.php", {"c": category})
        return data.get("meals") or []

    async def get_meal_by_id(self, meal_id: str) -> dict | None:
        data = await self._get_json("lookup.php", {"i": meal_id})
        meals = data.get("meals")
        return meals[0] if meals else None

    async def get_meals_by_ids(self, meal_ids: list[str]) -> list[dict]:
        meals = await asyncio.gather(
            *(self.get_meal_by_id(meal_id) for meal_id in meal_ids)
        )
        return [meal for meal in meals if meal is not None]

async def _demo() -> None:
    async with MealDBClient() as api:
        categories = await api.get_categories()
        print(categories)

        meals = await api.get_meals_by_category("Breakfast")
        print(f"Рецептов в категории: {len(meals)}")

        meal_ids = [meal["idMeal"] for meal in meals[:3]]
        full_meals = await api.get_meals_by_ids(meal_ids)

        for meal in full_meals:
            print(meal["strMeal"])


if __name__ == "__main__":
    asyncio.run(_demo())