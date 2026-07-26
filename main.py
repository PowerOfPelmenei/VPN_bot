import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

import config
from handlers import router, init_panel_api
from database import init_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Установка команд бота"""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="status", description="Статус подписки"),
        BotCommand(command="buy", description="Купить подписку"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)


async def main():
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")

    # Инициализация API панели
    init_panel_api()
    logger.info("API панели инициализирован")

    # Создание бота
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Установка команд
    await set_commands(bot)

    # Запуск бота
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())