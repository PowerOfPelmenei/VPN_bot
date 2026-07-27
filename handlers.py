import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import (
    get_user, create_user, update_user_subscription,
    deactivate_subscription, add_payment, update_payment_status
)
from panel_api import AsyncPanelAPI
from keyboards import (
    get_main_keyboard, get_tariff_keyboard,
    get_back_keyboard, get_subscription_info_keyboard
)
import config

router = Router()

# Инициализируем API панели (будет создан при старте бота)
panel_api: AsyncPanelAPI = None


def init_panel_api():
    """Инициализация API панели (вызывается при старте бота)"""
    global panel_api
    panel_api = AsyncPanelAPI(
        config.PANEL_URL,
        config.SUB_URL,
        config.SUB_PATH,
        config.XUI_TOKEN
    )


# --- Вспомогательные функции ---

def format_date(timestamp_ms: int) -> str:
    """Преобразует миллисекунды в читаемую дату"""
    if timestamp_ms == 0:
        return "Бессрочно"
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%d.%m.%Y %H:%M")


async def activate_subscription(user_id: int, tariff_key: str, tariff: dict) -> bool:
    """Активация подписки (общая логика)"""
    try:
        email = f"user_{user_id}"

        # Проверяем, существует ли клиент в панели
        client_data = await panel_api.get_client_by_email(email)

        if client_data:
            # Клиент существует - обновляем
            expire_time_ms = int((datetime.now() + timedelta(days=tariff["days"])).timestamp() * 1000)

            result = await panel_api.update_client(
                email,
                group=tariff["group"],
                expiryTime=expire_time_ms,
                enable=True
            )

            if not result.get("success"):
                return False

            # Получаем subId
            client_data = await panel_api.get_client_by_email(email)
            if client_data:
                client = client_data.get("client", {})
                sub_id = client.get("subId")
            else:
                sub_id = None
        else:
            # Клиент НЕ существует - создаем нового
            result = await panel_api.create_client(
                email=email,
                group_name=tariff["group"],
                expire_days=tariff["days"]
            )

            if not result.get("success"):
                return False

            # Получаем subId у нового клиента
            client_data = await panel_api.get_client_by_email(email)
            if client_data:
                client = client_data.get("client", {})
                sub_id = client.get("subId")
            else:
                sub_id = None

        # Обновляем БД
        update_user_subscription(
            user_id,
            tariff_key,
            tariff["days"],
            tariff["group"],
            sub_id
        )

        return True
    except Exception as e:
        print(f"Ошибка активации подписки: {e}")
        return False

# --- Обработчики команд ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Получаем или создаем пользователя ТОЛЬКО в БД
    user = get_user(user_id)
    if not user:
        user = create_user(user_id)
        # ❌ Убираем создание клиента в панели здесь

    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        "Я бот для управления VPN-подпиской.\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def cmd_help(event):
    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "📌 <b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/status - Проверить статус подписки\n"
        "/buy - Купить подписку\n"
        "/help - Помощь\n\n"
        "💡 <b>Как подключиться:</b>\n"
        "1. Купите подписку\n"
        "2. Получите ссылку\n"
        "3. Импортируйте в приложение (V2RayNG, Nekoray, Hiddify)\n\n"
        "❓ Вопросы: @support"
    )

    if isinstance(event, Message):
        await event.answer(text, parse_mode="HTML")
    else:
        await event.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )


@router.message(Command("status"))
@router.callback_query(F.data == "status")
async def cmd_status(event):
    user_id = event.from_user.id
    user = get_user(user_id)

    if not user:
        if isinstance(event, Message):
            await event.answer("❌ Вы не зарегистрированы. Используйте /start")
        else:
            await event.answer("❌ Вы не зарегистрированы", show_alert=True)
        return

    # Проверяем, есть ли клиент в панели
    client_data = None
    if panel_api:
        try:
            client_data = await panel_api.get_client_by_email(f"user_{user_id}")
        except Exception as e:
            print(f"Ошибка получения данных из панели: {e}")

    if not client_data:
        # Клиент еще не создан
        await event.message.edit_text(
            "📊 <b>Ваш статус подписки</b>\n\n"
            "❌ <b>Нет активной подписки</b>\n\n"
            "💡 Чтобы получить доступ, выберите тариф в разделе /buy",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return

    client = client_data.get("client", {})
    expiry_time = client.get("expiryTime", 0)
    is_enable = client.get("enable", False)
    group = client.get("group", "users")

    # Проверяем, активна ли подписка
    if expiry_time > 0 and expiry_time < datetime.now().timestamp() * 1000:
        is_enable = False
        await deactivate_subscription(user_id)

    status_text = "✅ <b>Активна</b>" if is_enable else "❌ <b>Не активна</b>"
    expiry_text = format_date(expiry_time) if expiry_time > 0 else "Не установлена"

    # Получаем ссылку только если подписка активна
    link_text = ""
    if is_enable:
        sub_url = await panel_api.get_subscription_url(f"user_{user_id}")
        if sub_url:
            link_text = f"\n\n🔗 <b>Ссылка для подключения:</b>\n<code>{sub_url}</code>"

    await event.message.edit_text(
        f"📊 <b>Ваш статус подписки</b>\n\n"
        f"Статус: {status_text}\n"
        f"Группа: {group}\n"
        f"Истекает: {expiry_text}\n"
        f"{link_text}",
        parse_mode="HTML",
        reply_markup=get_subscription_info_keyboard() if is_enable else get_main_keyboard()
    )

@router.message(Command("buy"))
@router.callback_query(F.data == "buy")
async def cmd_buy(event):
    user_id = event.from_user.id

    user = get_user(user_id)
    if not user:
        if isinstance(event, Message):
            await event.answer("❌ Вы не зарегистрированы. Используйте /start")
        else:
            await event.answer("❌ Вы не зарегистрированы", show_alert=True)
        return

    text = (
        "💎 <b>Выберите тариф:</b>\n\n"
        "🎁 <b>Пробный период</b> - 3 дня бесплатно\n"
        "💎 <b>1 месяц</b> - 100 ⭐ Stars\n"
        "💎 <b>3 месяца</b> - 250 ⭐ Stars\n\n"
        "⭐ <b>Как оплатить Stars?</b>\n"
        "1. Нажмите на кнопку с тарифом\n"
        "2. Подтвердите платеж в Telegram\n"
        "3. После оплаты подписка активируется автоматически"
    )

    if isinstance(event, Message):
        await event.answer(text, parse_mode="HTML", reply_markup=get_tariff_keyboard())
    else:
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=get_tariff_keyboard())


@router.callback_query(F.data == "back_to_menu")
async def cmd_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "👋 Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff(callback: CallbackQuery):
    tariff_key = callback.data.replace("tariff_", "")
    user_id = callback.from_user.id

    if tariff_key not in config.TARIFFS:
        await callback.answer("❌ Неверный тариф", show_alert=True)
        return

    tariff = config.TARIFFS[tariff_key]

    # Проверяем, есть ли уже активная подписка
    user = get_user(user_id)
    if user and user.subscription_active:
        # Если тариф бесплатный, не даем продлить
        if tariff["price"] == 0:
            await callback.answer("❌ У вас уже есть активная подписка", show_alert=True)
            return

    # Создаем платеж
    payment = add_payment(user_id, tariff_key, tariff["price"])

    if tariff["price"] == 0:
        # Бесплатный тариф (trial)
        await callback.message.edit_text(
            f"🎁 <b>Активация пробного периода</b>\n\n"
            f"Вы выбрали: {tariff['name']}\n"
            f"Срок: {tariff['days']} дней\n"
            f"Цена: Бесплатно\n\n"
            f"⏳ Подписка активируется...",
            parse_mode="HTML"
        )

        # Активируем подписку
        success = await activate_subscription(user_id, tariff_key, tariff)

        if success:
            # Получаем ссылку
            sub_url = await panel_api.get_subscription_url(f"user_{user_id}")

            await callback.message.edit_text(
                f"✅ <b>Пробный период активирован!</b>\n\n"
                f"Тариф: {tariff['name']}\n"
                f"Срок: {tariff['days']} дней\n\n"
                f"🔗 <b>Ваша ссылка:</b>\n"
                f"<code>{sub_url}</code>\n\n"
                f"📱 Импортируйте ссылку в приложение",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка активации</b>\n\n"
                "Не удалось активировать подписку. Попробуйте позже.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
    else:
        # Платный тариф
        await callback.message.edit_text(
            f"💎 <b>Оплата подписки</b>\n\n"
            f"Тариф: {tariff['name']}\n"
            f"Срок: {tariff['days']} дней\n"
            f"Цена: {tariff['price']} ⭐ Stars\n\n"
            f"⏳ Ожидайте подтверждения платежа...",
            parse_mode="HTML"
        )

        # Отправляем запрос на оплату через Telegram Stars
        try:
            # Создаем инвойс
            await callback.bot.send_invoice(
                chat_id=user_id,
                title=f"VPN {tariff['name']}",
                description=f"Подписка на {tariff['days']} дней",
                payload=f"payment_{payment.id}",
                currency="XTR",  # Telegram Stars
                prices=[{"label": tariff['name'], "amount": tariff['price']}],
                provider_token="",  # Для Stars не нужен
                start_parameter="vpn_bot"
            )

            await callback.message.edit_text(
                f"💎 <b>Ожидание оплаты</b>\n\n"
                f"Тариф: {tariff['name']}\n"
                f"Сумма: {tariff['price']} ⭐ Stars\n\n"
                f"📩 Нажмите на кнопку <b>Оплатить</b> в сообщении ниже",
                parse_mode="HTML",
                reply_markup=get_back_keyboard()
            )
        except Exception as e:
            print(f"Ошибка создания инвойса: {e}")
            await callback.message.edit_text(
                "❌ <b>Ошибка создания платежа</b>\n\n"
                "Попробуйте позже.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )


@router.callback_query(F.data == "refresh")
async def cmd_refresh(callback: CallbackQuery):
    """Обновить ссылку подписки"""
    user_id = callback.from_user.id

    if not panel_api:
        await callback.answer("⏳ Сервис временно недоступен", show_alert=True)
        return

    try:
        sub_url = await panel_api.get_subscription_url(f"user_{user_id}")
        if sub_url:
            await callback.message.edit_text(
                f"🔗 <b>Ваша ссылка для подключения</b>\n\n"
                f"<code>{sub_url}</code>\n\n"
                f"📱 Импортируйте эту ссылку в приложение:\n"
                f"• V2RayNG\n"
                f"• Nekoray\n"
                f"• Hiddify\n"
                f"• и другие",
                parse_mode="HTML",
                reply_markup=get_subscription_info_keyboard()
            )
        else:
            # Проверяем, есть ли активная подписка
            user = get_user(user_id)
            if user and user.subscription_active:
                await callback.message.edit_text(
                    "❌ <b>Не удалось получить ссылку</b>\n\n"
                    "Возможно, клиент еще не создан в панели.\n"
                    "Попробуйте обновить статус через /status",
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "❌ <b>У вас нет активной подписки</b>\n\n"
                    "Купите подписку в разделе /buy",
                    parse_mode="HTML",
                    reply_markup=get_main_keyboard()
                )
    except Exception as e:
        print(f"Ошибка получения ссылки: {e}")
        await callback.answer("❌ Ошибка получения ссылки", show_alert=True)


# --- Обработчики платежей ---

@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query):
    """Обработка предварительного запроса на оплату"""
    await pre_checkout_query.bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True
    )


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешной оплаты"""
    user_id = message.from_user.id
    payment_info = message.successful_payment

    # Извлекаем ID платежа из payload
    payload = payment_info.invoice_payload
    payment_id = int(payload.replace("payment_", ""))

    # Обновляем статус платежа
    payment = update_payment_status(payment_id, "success")
    if not payment:
        await message.answer("❌ Ошибка обработки платежа")
        return

    # Находим тариф
    tariff_key = payment.tariff
    tariff = config.TARIFFS.get(tariff_key)
    if not tariff:
        await message.answer("❌ Неизвестный тариф")
        return

    # Активируем подписку
    await message.answer(
        f"✅ <b>Оплата получена!</b>\n\n"
        f"Активируем подписку...",
        parse_mode="HTML"
    )

    success = await activate_subscription(user_id, tariff_key, tariff)

    if success:
        # Получаем ссылку
        sub_url = await panel_api.get_subscription_url(f"user_{user_id}")

        await message.answer(
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"Тариф: {tariff['name']}\n"
            f"Срок: {tariff['days']} дней\n\n"
            f"🔗 <b>Ваша ссылка:</b>\n"
            f"<code>{sub_url}</code>\n\n"
            f"📱 Импортируйте ссылку в приложение",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Ошибка активации подписки</b>\n\n"
            "Платеж получен, но не удалось активировать подписку.\n"
            "Обратитесь в поддержку: @support",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )