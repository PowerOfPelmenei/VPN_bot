import asyncio
from panel_api import AsyncPanelAPI
import config
from datetime import datetime, timedelta


async def manual_update():
    api = AsyncPanelAPI(
        config.PANEL_URL,
        config.SUB_URL,
        config.SUB_PATH,
        config.XUI_TOKEN
    )

    # ЗАМЕНИТЕ НА СВОЙ TELEGRAM ID
    user_id = 1426184917  # <-- СЮДА ВСТАВЬТЕ СВОЙ ID

    email = f"user_{user_id}"

    print("=" * 60)
    print("1. Получаем клиента...")
    print("=" * 60)
    client_data = await api.get_client_by_email(email)
    print(f"Клиент: {client_data}")

    if client_data:
        client = client_data.get("client", {})
        print(f"Текущий срок: {client.get('expiryTime')}")
        print(f"Текущая группа: {client.get('group')}")

        # Устанавливаем новый срок +30 дней
        new_expiry = int((datetime.now() + timedelta(days=30)).timestamp() * 1000)
        print(f"Новый срок: {new_expiry}")

        print("\n" + "=" * 60)
        print("2. Обновляем клиента...")
        print("=" * 60)
        result = await api.update_client(
            email,
            group="Monthly",
            expiryTime=new_expiry,
            enable=True
        )
        print(f"Результат: {result}")

        print("\n" + "=" * 60)
        print("3. Проверяем обновленный срок...")
        print("=" * 60)
        client_data = await api.get_client_by_email(email)
        if client_data:
            client = client_data.get("client", {})
            print(f"Новый срок: {client.get('expiryTime')}")
            print(f"Новая группа: {client.get('group')}")
    else:
        print("❌ Клиент не найден!")

    await api.close()


asyncio.run(manual_update())