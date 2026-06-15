# panel_api.py
import logging
import time
import uuid
import urllib.parse
from typing import Dict, Optional

import py3xui
from py3xui import AsyncApi
from py3xui.inbound import Inbound

from config import (
    PANEL_HOST, PANEL_USERNAME, PANEL_PASSWORD,
    INBOUND_REMARKS, LINK_TEMPLATES
)
from database import get_user, update_subscription_end

api = AsyncApi(
    host=PANEL_HOST,
    username=PANEL_USERNAME,
    password=PANEL_PASSWORD
)

_inbounds_by_id: Dict[int, Inbound] = {}
_remark_to_id: Dict[str, int] = {}


async def refresh_inbounds_cache():
    global _inbounds_by_id, _remark_to_id
    await api.login()
    inbounds = await api.inbound.get_list()
    _inbounds_by_id = {ib.id: ib for ib in inbounds}
    _remark_to_id = {ib.remark: ib.id for ib in inbounds}
    logging.info(f"Кэш inbound-ов обновлён. Найдено: {len(_inbounds_by_id)}")


async def get_inbound_by_id(inbound_id: int) -> Optional[Inbound]:
    if not _inbounds_by_id:
        await refresh_inbounds_cache()
    return _inbounds_by_id.get(inbound_id)


async def get_inbound_id_by_remark(remark: str) -> Optional[int]:
    if not _remark_to_id:
        await refresh_inbounds_cache()
    return _remark_to_id.get(remark)


async def create_or_update_client_in_inbound(inbound_id: int, email: str, uuid_str: str, expiry: int):
    inbound = await get_inbound_by_id(inbound_id)
    if not inbound:
        raise ValueError(f"Inbound {inbound_id} not found")

    existing_client = None
    for cl in inbound.settings.clients:
        if cl.email == email:
            existing_client = cl
            break

    if existing_client:
        existing_client.expiry_time = expiry
        existing_client.total_gb = 0
        existing_client.enable = True
        existing_client.password = uuid_str

        if inbound.protocol == 'vless' and inbound.stream_settings and inbound.stream_settings.security == 'reality':
            existing_client.flow = "xtls-rprx-vision"

        await api.client.update(inbound_id, existing_client)
        logging.info(f"Обновлён клиент {email} в inbound {inbound_id}")
    else:
        new_client = py3xui.Client(
            id=uuid_str,
            email=email,
            password=uuid_str,
            enable=True,
            total_gb=0,
            expiry_time=expiry,
            limit_ip=0
        )
        if inbound.protocol == 'vless' and inbound.stream_settings and inbound.stream_settings.security == 'reality':
            new_client.flow = "xtls-rprx-vision"

        await api.client.add(inbound_id, [new_client])
        logging.info(f"Создан клиент {email} в inbound {inbound_id}")

    # Обновляем кэш после изменений
    all_inbounds = await api.inbound.get_list()
    for ib in all_inbounds:
        _inbounds_by_id[ib.id] = ib
        _remark_to_id[ib.remark] = ib.id


def get_client_link(remark: str, uuid_str: str, user_id: int) -> str:
    """Генерирует ссылку по шаблону"""
    template = LINK_TEMPLATES.get(remark)
    if not template:
        return f"❌ Нет шаблона для {remark}"
    remark_suffix = f"{remark}-user_{user_id}_{remark.replace(' ', '_')}"
    link = template.format(uuid=uuid_str, remark_suffix=urllib.parse.quote(remark_suffix))
    return link


async def create_or_update_subscription(user_id: int, days: int, ignore_trial_flag: bool = False) -> Dict[str, str]:
    """
    Создаёт или обновляет клиентов во всех inbound-ах.
    Возвращает словарь {remark: ссылка}
    """
    base_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{user_id}"))
    new_expiry = int((time.time() + days * 86400) * 1000)  # миллисекунды

    user = get_user(user_id)
    current_end = user.get('subscription_end', 0) if user else 0
    if current_end > int(time.time() * 1000):
        new_expiry = current_end + days * 86400 * 1000

    await refresh_inbounds_cache()

    links = {}
    for remark in INBOUND_REMARKS:
        inbound_id = await get_inbound_id_by_remark(remark)
        if not inbound_id:
            links[remark] = f"❌ Inbound '{remark}' не найден"
            continue

        email = f"user_{user_id}_{remark.replace(' ', '_')}"
        try:
            await create_or_update_client_in_inbound(inbound_id, email, base_uuid, new_expiry)
            link = get_client_link(remark, base_uuid, user_id)
            links[remark] = link if link else "⚠️ Ссылка не сгенерирована"
        except Exception as e:
            logging.error(f"Ошибка обработки inbound {remark}: {e}")
            links[remark] = f"❌ Ошибка: {str(e)}"

    update_subscription_end(user_id, new_expiry)
    return links