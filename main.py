import asyncio
from datetime import datetime, timedelta
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

import config
from handlers import router, init_panel_api
from database import init_db, get_expiring_subscriptions

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


# async def check_expiring_subscriptions(bot: Bot):
#     """Проверка подписок, истекающих через 3 дня"""
#     while True:
#         try:
#             expiring_users = get_expiring_subscriptions(days_before=3)
#
#             for user in expiring_users:
#                 days_left = (user.subscription_end - datetime.now()).days
#                 if days_left <= 3:
#                     await bot.send_message(
#                         chat_id=user.telegram_id,
#                         text=f"⚠️ <b>Внимание!</b>\n\n"
#                              f"Ваша подписка истекает через <b>{days_left}</b> дня(ей).\n\n"
#                              f"Продлите подписку, чтобы не потерять доступ:\n"
#                              f"/buy",
#                         parse_mode="HTML"
#                     )
#                     print(f"📨 Уведомление отправлено пользователю {user.telegram_id}")
#
#             # Проверяем раз в 12 часов
#             await asyncio.sleep(43200)  # 12 часов
#
#         except Exception as e:
#             print(f"❌ Ошибка проверки подписок: {e}")
#             await asyncio.sleep(3600)  # При ошибке ждём час

async def main():
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")

    # Инициализация API панели
    init_panel_api()
    logger.info("API панели инициализирован")

    # Создание бота
    bot = Bot(token=config.BOT_TOKEN)
    # await asyncio.create_task(check_expiring_subscriptions(bot))
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