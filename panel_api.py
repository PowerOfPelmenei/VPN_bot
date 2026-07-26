import httpx
import json
import base64
import time
from urllib.parse import urljoin
from typing import Optional, Dict, Any, List


class AsyncPanelAPI:
    """Асинхронный клиент для работы с 3x-ui панелью"""

    def __init__(self, panel_url: str, sub_url: str, sub_path: str, token: str):
        """
        Инициализация API панели

        Args:
            panel_url: URL панели (например, https://ru-panel.konoha.us.ci:23168/229XmnXsbkeTr8J7Xr)
            sub_url: URL для подписок (например, https://ru-panel.konoha.us.ci:2096)
            sub_path: Путь для подписок (например, gdfhskjlfsdfgn)
            token: Токен авторизации
        """
        self.panel_url = panel_url.rstrip('/')
        self.sub_url = sub_url.rstrip('/')
        self.sub_path = sub_path.strip('/')
        self.token = token

        # Создаем асинхронный клиент
        self.client = httpx.AsyncClient(
            verify=False,  # Отключаем проверку SSL (для самоподписанных сертификатов)
            timeout=30.0  # Таймаут на запросы
        )

        # Отключаем предупреждения о SSL
        import warnings
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    async def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов"""
        return {
            'accept': "application/json",
            'Authorization': f"Bearer {self.token}",
            'Content-Type': "application/json"
        }

    async def get_inbounds(self) -> List[Dict[str, Any]]:
        """
        Получить список всех inbound'ов

        Returns:
            Список inbound'ов
        """
        url = urljoin(self.panel_url + "/", "panel/api/inbounds/list")
        response = await self.client.get(url, headers=await self._get_headers())

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("obj", [])
        return []

    async def get_groups(self) -> List[Dict[str, Any]]:
        """
        Получить список всех групп

        Returns:
            Список групп
        """
        url = urljoin(self.panel_url + "/", "panel/api/clients/groups")
        response = await self.client.get(url, headers=await self._get_headers())

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("obj", [])
        return []

    async def create_client(self, email: str, group_name: str, expire_days: int) -> Dict[str, Any]:
        """
        Создать клиента с привязкой к группе

        Args:
            email: Email клиента (обычно telegram_id)
            group_name: Название группы (Trial, Monthly, Quarterly)
            expire_days: Срок действия в днях

        Returns:
            Ответ от API
        """
        # Получаем список inbound'ов
        inbounds = await self.get_inbounds()
        inbound_ids = [inbound['id'] for inbound in inbounds]
        # Вычисляем время истечения в МИЛЛИСЕКУНДАХ (как в примере API)
        import time
        expire_time_ms = int((time.time() + expire_days * 86400) * 1000) if expire_days > 0 else 0

        # Данные для создания клиента
        client_data = {
            "client": {
                "email": email,  # используем переданный email
                "totalGB": 0,  # 0 = безлимит
                "expiryTime": expire_time_ms,
                "tgid": 0,  # обратите внимание: tgid (маленькая буква)
                "limitIp": 0,
                "enable": True,
                "flow": "xtls-rprx-vision",  # Устанавливаем flow при создании
                "group": "users"  # Группа по умолчанию
            },
            "inboundIds": inbound_ids
        }

        print(f"Отправляем данные: {json.dumps(client_data, indent=2)}")

        # Отправляем запрос на создание клиента
        url = urljoin(self.panel_url + "/", "panel/api/clients/add")
        response = await self.client.post(
            url,
            json=client_data,
            headers=await self._get_headers())

        if response.status_code == 200:
            return response.json()
        return {
            "success": False,
            "error": f"HTTP {response.status_code}",
            "response": response.text
        }

    async def update_client(self, email: str, **kwargs) -> Dict[str, Any]:
        """
        Обновить данные клиента (полная замена)

        Args:
            email: Email клиента
            **kwargs: Поля для обновления (group, expiryTime, enable, flow и т.д.)

        Returns:
            Ответ от API
        """
        # 1. Получаем текущие данные клиента
        client_data = await self.get_client_by_email(email)
        if not client_data:
            return {"success": False, "error": "Клиент не найден"}

        client = client_data.get("client", {})

        # 2. Обновляем только переданные поля
        for key, value in kwargs.items():
            client[key] = value
        # 3. Убираем поля, которые не нужно отправлять на обновление
        # Они есть в ответе, но не нужны для update
        fields_to_remove = ['id', 'createdAt', 'updatedAt', 'reset', 'comment', 'auth', 'password']
        for field in fields_to_remove:
            client.pop(field, None)

        # 4. Отправляем полный набор данных
        url = urljoin(self.panel_url + "/", f"panel/api/clients/update/{email}")
        response = await self.client.post(
            url,
            json=client,  # отправляем весь объект client
            headers=await self._get_headers()
        )

        if response.status_code == 200:
            return response.json()
        return {
            "success": False,
            "error": f"HTTP {response.status_code}",
            "response": response.text
        }

    async def get_client_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получить клиента по email

        Args:
            email: Email клиента

        Returns:
            Данные клиента или None
        """
        url = urljoin(self.panel_url + "/", f"panel/api/clients/get/{email}")
        response = await self.client.get(url, headers=await self._get_headers())

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("obj")
        return None

    async def get_subscription_url(self, email: str) -> Optional[str]:
        """
        Получить ссылку на подписку для клиента

        Формат: {SUB_URL}/{sub_path}/{sub_uuid}/

        Args:
            email: Email клиента

        Returns:
            Ссылка на подписку или None
        """
        client_data = await self.get_client_by_email(email)
        client = client_data.get("client")
        if client:
            # Пробуем получить subId, если нет - берем uuid
            sub_uuid = client.get('subId')
            if sub_uuid:
                return f"{self.sub_url}/{self.sub_path}/{sub_uuid}"
        return None

    async def get_client_links(self, email: str) -> Optional[List[str]]:
        """
        Получить все ссылки клиента (для отладки)

        Args:
            email: Email клиента

        Returns:
            Список ссылок или None
        """
        sub_url = await self.get_subscription_url(email)
        if sub_url:
            response = await self.client.get(sub_url, headers=await self._get_headers())
            if response.status_code == 200:
                try:
                    # Пробуем декодировать base64
                    decoded = base64.b64decode(response.text).decode('utf-8')
                    return decoded.strip().split('\n')
                except:
                    # Если не base64, возвращаем как есть
                    return [response.text]
        return None

    async def delete_client(self, email: str) -> Dict[str, Any]:
        """
        Удалить клиента по email

        Args:
            email: Email клиента

        Returns:
            Ответ от API
        """
        url = urljoin(self.panel_url + "/", f"panel/api/clients/del/{email}")
        response = await self.client.post(url, headers=await self._get_headers())

        if response.status_code == 200:
            return response.json()
        return {
            "success": False,
            "error": f"HTTP {response.status_code}",
            "response": response.text
        }

    async def get_all_clients(self) -> List[Dict[str, Any]]:
        """
        Получить всех клиентов

        Returns:
            Список всех клиентов
        """
        url = urljoin(self.panel_url + "/", "panel/api/clients/list")
        response = await self.client.get(url, headers=await self._get_headers())
        print(response)
        if response.status_code == 200:
            data = response.json()
            # print(data)
            if data.get("success"):
                return data.get("obj", [])
        return []

    async def close(self):
        """Закрыть HTTP-клиент"""
        await self.client.aclose()