import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN. "
        "Создайте файл .env по образцу .env.example"
    )