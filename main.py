import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from panel_api import refresh_inbounds_cache
from handlers import register_handlers

async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных
    init_db()
    logging.info("✅ База данных инициализирована")

    # Загрузка кэша инбаундов из панели 3x-ui
    try:
        await refresh_inbounds_cache()
        logging.info("✅ Подключено к 3x-ui, кэш инбаундов загружен")
    except Exception as e:
        logging.error(f"⚠️ Ошибка подключения к панели 3x-ui: {e}")

    # Регистрация всех обработчиков
    register_handlers(dp)
    logging.info("✅ Обработчики зарегистрированы")

    # Запуск поллинга
    logging.info("🚀 Бот запущен и начал приём сообщений")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())