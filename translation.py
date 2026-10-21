import asyncio
import logging

from googletrans import Translator

logger = logging.getLogger(__name__)

TARGET_LANGUAGE = "ru"
MAX_CONCURRENT_TRANSLATIONS=5

async def _translate_one(
        translator:Translator,
        text:str,
        semaphore:asyncio.Semaphore
) -> str:
    if not text or not text.strip():
        return text

    async with semaphore:
        try:
            result = await translator.translate(text, dest=TARGET_LANGUAGE)
            return result.text
        except Exception as error:
            logger.warning("Не удалось перевести текст: %s", error)
            return text

async def translate_texts(texts: list[str]) -> list[str]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSLATIONS)

    async with Translator() as translator:
        return await asyncio.gather(
            *(_translate_one(translator, text, semaphore) for text in texts)
        )

async def translate_text(text: str) -> str:
    translated = await translate_texts([text])
    return translated[0]

async def _demo() -> None:
    titles = ["Bread omelette", "Breakfast Potatoes", ""]
    print(await translate_texts(titles))
    print(await translate_text("Preheat the oven to 200 degrees."))


if __name__ == "__main__":
    asyncio.run(_demo())