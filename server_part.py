import asyncio
import logging
import time
import uuid
import py3xui
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from py3xui import AsyncApi

# ---------- 1. КОНФИГУРАЦИЯ (замените на свои данные) ----------
BOT_TOKEN = "8473341751:AAFV9yIIxbwTO5t-WvkG_9wEB9QOA65jvPM"

PANEL_HOST = "http://89.127.209.251:23168/229XmnXsbkeTr8J7Xr"
PANEL_USERNAME = "ZklMcpInoM"
PANEL_PASSWORD = "jS57thNqgw"
# -----------------------------------------------------------------

logging.basicConfig(level=logging.INFO)

# ---------- 2. СОЗДАНИЕ ЭКЗЕМПЛЯРОВ КЛАССОВ ----------
# Экземпляр API панели
api = AsyncApi(
    host=PANEL_HOST,
    username=PANEL_USERNAME,
    password=PANEL_PASSWORD
)

# Экземпляр бота и диспетчера с хранилищем для FSM
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------- 3. FSM: состояния для создания клиента ----------
class NewClientStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_limit_gb = State()
    waiting_for_days = State()

# ---------- 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def parse_limit_gb(text: str) -> int:
    """Преобразует '10', '10GB', '10 gb' в число гигабайт."""
    text = text.lower().replace('gb', '').replace(' ', '')
    return int(float(text))

def parse_days(text: str) -> int:
    """Преобразует '30', '30d', '30 days' в число дней."""
    text = text.lower().replace('дн', '').replace('day', '').replace('days', '').replace('d', '').strip()
    days = int(float(text))
    if days <= 0:
        raise ValueError
    return days

# ---------- 5. ОБРАБОТЧИКИ КОМАНД ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        await api.login()
        inbounds = await api.inbound.get_list()
        await message.answer(
            f"👋 Бот для управления 3x-ui\n"
            f"Inbound-ов: {len(inbounds)}\n"
            f"/clients — список клиентов\n"
            f"/new_client — создать нового клиента"
        )
    except Exception as e:
        logging.error(f"Start error: {e}")
        await message.answer("❌ Не удалось подключиться к панели.")

@dp.message(Command("clients"))
async def cmd_clients(message: types.Message):
    try:
        await api.login()
        inbounds = await api.inbound.get_list()
        if not inbounds:
            await message.answer("Нет inbound-ов.")
            return
        inbound = inbounds[0]  # берём первый попавшийся
        clients = inbound.settings.clients
        if not clients:
            await message.answer(f"В inbound `{inbound.remark}` клиентов нет.")
            return
        client_list = "\n".join([f"- {c.email}" for c in clients[:10]])
        await message.answer(f"📋 Последние клиенты в `{inbound.remark}`:\n{client_list}")
    except Exception as e:
        logging.error(f"Clients error: {e}")
        await message.answer("❌ Ошибка получения списка клиентов.")

@dp.message(Command("new_client"))
async def cmd_new_client(message: types.Message, state: FSMContext):
    await state.set_state(NewClientStates.waiting_for_email)
    await message.answer("✉️ Введите **email** нового клиента (например, user@example.com):")

@dp.message(StateFilter(NewClientStates.waiting_for_email))
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    print(email)
    if not email:
        await message.answer("Email не может быть пустым. Попробуйте снова:")
        return
    await state.update_data(email=email)
    await state.set_state(NewClientStates.waiting_for_limit_gb)
    await message.answer("📊 Введите **лимит трафика** в гигабайтах (например, 100 или 10GB):")

@dp.message(StateFilter(NewClientStates.waiting_for_limit_gb))
async def process_limit(message: types.Message, state: FSMContext):
    try:
        limit_gb = parse_limit_gb(message.text)
        print(limit_gb)
        await state.update_data(limit_gb=limit_gb)
        await state.set_state(NewClientStates.waiting_for_days)
        await message.answer("📅 Введите **срок действия** в днях (например, 30):")
    except ValueError:
        await message.answer("❌ Некорректное число. Укажите количество гигабайт (цифрами).")

@dp.message(StateFilter(NewClientStates.waiting_for_days))
async def process_days(message: types.Message, state: FSMContext):
    try:
        days = parse_days(message.text)
        print(days)
        user_data = await state.get_data()
        print(user_data)
        email = user_data["email"]
        limit_gb = user_data["limit_gb"]

        # Авторизация в панели
        await api.login()

        # Получаем список inbound'ов
        inbounds = await api.inbound.get_list()
        if not inbounds:
            await message.answer("❌ В панели нет inbound-ов. Добавьте хотя бы один вручную.")
            await state.clear()
            return

        # Берём первый inbound (можно потом доработать выбор)
        target_inbound = inbounds[0]

        # Вычисляем expiry_time (timestamp)
        expiry = int(time.time() + days * 86400)

        # Лимит в байтах
        total_bytes = limit_gb * 1024 * 1024 * 1024

        # Создаём клиента (метод может называться add_client в некоторых версиях)
        # Пробуем оба варианта
        try:
            new_client = py3xui.Client(id=str(uuid.uuid4()), email=email, enable=True)
            inbound_id = 2
            # Вариант 1 (актуальный для py3xui >= 2.0)
            await  api.client.add(inbound_id, [new_client])
            print("roflan")
            # new_client = await api.client.add(
            #     inbound_id=target_inbound.id,
            #     email=email,
            #     total_gb=total_bytes,
            #     expiry_time=expiry,
            #     enable=True,
            #     limit_ip=1
            # )
        except AttributeError:
            # Вариант 2 (старые версии)
            new_client = await api.add_client(
                inbound_id=target_inbound.id,
                email=email,
                total_gb=total_bytes,
                expiry_time=expiry,
                enable=True,
                limit_ip=1
            )

        # Пытаемся получить ссылку на подключение
        if hasattr(new_client, 'link') and new_client.link:
            link = new_client.link
        elif hasattr(new_client, 'get_link'):
            link = new_client.get_link()
        else:
            try:
                link = await api.client.get_by_email(email)
                print(link)
            except:
                link = "Ссылку не удалось получить, проверьте панель вручную."

        await message.answer(
            f"✅ Клиент **{email}** создан!\n"
            f"📊 Лимит: {limit_gb} GB\n"
            f"⏳ Дней: {days}\n"
            f"🔗 Ссылка:\n`{link}`",
            parse_mode="Markdown"
        )
        await state.clear()

    except Exception as e:
        logging.error(f"Create client error: {e}")
        await message.answer(f"❌ Ошибка при создании клиента: {str(e)}")
    await state.clear()


# ---------- 6. ЗАПУСК ЭКЗЕМПЛЯРА БОТА ----------
async def main():
    # При старте проверяем авторизацию
    try:
        await api.login()
        logging.info("✅ Авторизация в 3x-ui успешна")
    except Exception as e:
        logging.error(f"⚠️ Не удалось авторизоваться при старте: {e}")

    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())