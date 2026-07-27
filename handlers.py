import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from database import (
    get_user, create_user, update_user_subscription,
    deactivate_subscription, add_payment, update_payment_status,
    delete_user, add_payment_and_get_id, get_payment_by_id
)
from panel_api import AsyncPanelAPI
from keyboards import (
    get_main_keyboard, get_tariff_keyboard,
    get_back_keyboard, get_subscription_info_keyboard
)
import config

router = Router()

# Инициализируем API панели
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


async def get_client_or_none(email: str):
    """Получить клиента из панели или None"""
    try:
        client_data = await panel_api.get_client_by_email(email)
        if client_data:
            return client_data.get("client", {})
    except Exception as e:
        print(f"Ошибка получения клиента: {e}")
    return None


async def activate_subscription(user_id: int, tariff_key: str, tariff: dict) -> bool:
    """Активация подписки с поддержкой продления (суммирование времени)"""
    try:
        email = f"user_{user_id}"
        print(f"🔄 Активация подписки для {email}, тариф: {tariff['name']}")

        # Проверяем, существует ли клиент
        client_data = await panel_api.get_client_by_email(email)
        print(f"   Клиент в панели: {'найден' if client_data else 'не найден'}")

        if client_data:
            client = client_data.get("client", {})

            # Получаем текущее время истечения
            current_expiry = client.get("expiryTime", 0)
            current_time_ms = int(datetime.now().timestamp() * 1000)

            print(f"   Текущий срок: {current_expiry}, текущее время: {current_time_ms}")

            # Если срок еще не истек, добавляем дни к текущему сроку
            if current_expiry > current_time_ms:
                # Добавляем дни к существующему сроку
                new_expiry = current_expiry + (tariff["days"] * 24 * 60 * 60 * 1000)
                print(f"   Продление: новый срок {new_expiry}")
            else:
                # Если срок истек, устанавливаем новый срок от текущего момента
                new_expiry = int((datetime.now() + timedelta(days=tariff["days"])).timestamp() * 1000)
                print(f"   Новая подписка: срок {new_expiry}")

            # Обновляем клиента
            update_data = {
                "email": email,
                "group": tariff["group"],
                "expiryTime": new_expiry,
                "enable": True,
                "totalGB": client.get("totalGB", 0),
                "tgid": client.get("tgid", 0),
                "limitIp": client.get("limitIp", 0),
                "flow": client.get("flow", "xtls-rprx-vision")
            }

            print(f"   Отправляем update: {update_data}")
            result = await panel_api.update_client(email, **update_data)
            print(f"   Результат update: {result}")

            if not result.get("success"):
                print(f"❌ Ошибка обновления клиента: {result}")
                return False
        else:
            # Создаем нового клиента
            print(f"   Создаем нового клиента")
            result = await panel_api.create_client(
                email=email,
                group_name=tariff["group"],
                expire_days=tariff["days"]
            )
            print(f"   Результат create: {result}")

            if not result.get("success"):
                print(f"❌ Ошибка создания клиента: {result}")
                return False

        # Получаем subId
        client_data = await panel_api.get_client_by_email(email)
        sub_id = None
        if client_data:
            client = client_data.get("client", {})
            sub_id = client.get("subId")
            print(f"   subId: {sub_id}")

        # Обновляем БД
        update_user_subscription(
            user_id,
            tariff_key,
            tariff["days"],
            tariff["group"],
            sub_id
        )
        print(f"✅ Подписка успешно активирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка активации подписки: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- Обработчики команд ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Только БД, без создания клиента
    user = get_user(user_id)
    if not user:
        user = create_user(user_id)

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

    client = await get_client_or_none(f"user_{user_id}")

    if not client:
        if user.subscription_active:
            deactivate_subscription(user_id)

        text = (
            "📊 <b>Ваш статус подписки</b>\n\n"
            "❌ <b>Нет активной подписки</b>\n\n"
            "💡 Чтобы получить доступ, выберите тариф в разделе /buy"
        )

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())
        else:
            await event.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())
        return

    expiry_time = client.get("expiryTime", 0)
    is_enable = client.get("enable", False)

    # Проверяем, активна ли подписка
    if expiry_time > 0 and expiry_time < datetime.now().timestamp() * 1000:
        is_enable = False
        deactivate_subscription(user_id)

    status_text = "✅ <b>Активна</b>" if is_enable else "❌ <b>Не активна</b>"
    expiry_text = format_date(expiry_time) if expiry_time > 0 else "Не установлена"

    # Получаем ссылку только если подписка активна
    link_text = ""
    if is_enable:
        sub_url = await panel_api.get_subscription_url(f"user_{user_id}")
        if sub_url:
            link_text = f"\n\n🔗 <b>Ссылка для подключения:</b>\n<code>{sub_url}</code>"

    text = (
        f"📊 <b>Ваш статус подписки</b>\n\n"
        f"Статус: {status_text}\n"
        f"Истекает: {expiry_text}\n"
        f"{link_text}"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_subscription_info_keyboard() if is_enable else get_main_keyboard()
        )
    else:
        await event.answer(
            text,
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
    user = get_user(user_id)

    # Проверяем, есть ли клиент в панели
    client = await get_client_or_none(f"user_{user_id}")

    # Проверяем, не пытается ли пользователь взять пробный период повторно
    if tariff["price"] == 0 and client:
        await callback.answer("❌ Пробный период доступен только один раз", show_alert=True)
        return

    # Создаем платеж и сразу получаем ID
    payment_id = add_payment_and_get_id(user_id, tariff_key, tariff["price"])

    if tariff["price"] == 0:
        # Бесплатный тариф (trial) — без изменений
        await callback.message.edit_text(
            f"🎁 <b>Активация пробного периода</b>\n\n"
            f"Вы выбрали: {tariff['name']}\n"
            f"Срок: {tariff['days']} дней\n"
            f"Цена: Бесплатно\n\n"
            f"⏳ Подписка активируется...",
            parse_mode="HTML"
        )

        success = await activate_subscription(user_id, tariff_key, tariff)

        if success:
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
        await callback.answer()
        return

    # --- Платный тариф ---
    # Проверяем, активна ли уже подписка (для отображения)
    is_renewal = False
    if client:
        expiry_time = client.get("expiryTime", 0)
        is_enable = client.get("enable", False)
        current_time_ms = int(datetime.now().timestamp() * 1000)
        if is_enable and expiry_time > current_time_ms:
            is_renewal = True

    renewal_text = " (продление)" if is_renewal else ""

    # Создаем клавиатуру с кнопкой "Оплатить"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"💎 Оплатить {tariff['price']} ⭐",
                callback_data=f"pay_{payment_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_menu"
            )
        ]
    ])

    # ОДНО сообщение с информацией и кнопкой "Оплатить"
    await callback.message.edit_text(
        f"💎 <b>Оплата подписки{renewal_text}</b>\n\n"
        f"Тариф: {tariff['name']}\n"
        f"Срок: {tariff['days']} дней\n"
        f"Цена: {tariff['price']} ⭐ Stars\n\n"
        f"Нажмите кнопку <b>Оплатить</b> для завершения платежа.",
        parse_mode="HTML",
        reply_markup=payment_keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Оплатить'"""
    payment_id = int(callback.data.replace("pay_", ""))
    user_id = callback.from_user.id

    # Получаем информацию о платеже
    from database import get_payment_by_id
    payment = get_payment_by_id(payment_id)

    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return

    # Находим тариф
    tariff_key = payment.tariff
    tariff = config.TARIFFS.get(tariff_key)
    if not tariff:
        await callback.answer("❌ Неизвестный тариф", show_alert=True)
        return

    # Обновляем сообщение — показываем, что ожидаем оплату
    # Убираем кнопку "Оплатить", оставляем только "Назад"
    await callback.message.edit_text(
        f"⏳ <b>Ожидание оплаты</b>\n\n"
        f"Тариф: {tariff['name']}\n"
        f"Сумма: {tariff['price']} ⭐ Stars\n\n"
        f"Нажмите на кнопку <b>Оплатить</b> в сообщении ниже.",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

    try:
        # Отправляем инвойс отдельным сообщением
        await callback.bot.send_invoice(
            chat_id=user_id,
            title=f"VPN {tariff['name']}",
            description=f"Подписка на {tariff['days']} дней",
            payload=f"payment_{payment_id}",
            currency="XTR",
            prices=[{"label": tariff['name'], "amount": tariff['price']}],
            provider_token="",
            # Добавляем параметры для лучшего отображения
            start_parameter="vpn_subscription",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
    except Exception as e:
        print(f"Ошибка создания инвойса: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка создания платежа</b>\n\n"
            f"Текст ошибки: {str(e)}\n\n"
            f"Попробуйте позже или выберите другой тариф.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "refresh")
async def cmd_refresh(callback: CallbackQuery):
    """Обновить ссылку подписки"""
    user_id = callback.from_user.id

    if not panel_api:
        await callback.answer("⏳ Сервис временно недоступен", show_alert=True)
        return

    # Проверяем, есть ли клиент
    client = await get_client_or_none(f"user_{user_id}")

    if not client:
        await callback.message.edit_text(
            "❌ <b>У вас нет активной подписки</b>\n\n"
            "Клиент не найден в системе.\n"
            "Купите подписку в разделе /buy",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    is_enable = client.get("enable", False)
    expiry_time = client.get("expiryTime", 0)

    # Проверяем, активна ли подписка
    if not is_enable or (expiry_time > 0 and expiry_time < datetime.now().timestamp() * 1000):
        deactivate_subscription(user_id)
        await callback.message.edit_text(
            "❌ <b>Ваша подписка не активна</b>\n\n"
            "Срок действия истек или подписка отключена.\n"
            "Купите новую подписку в разделе /buy",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
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
            await callback.message.edit_text(
                "❌ <b>Не удалось получить ссылку</b>\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        print(f"Ошибка получения ссылки: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка получения ссылки</b>\n\n"
            f"Текст ошибки: {str(e)}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()


# --- Обработчики платежей ---

@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
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

    print("=" * 60)
    print("✅ ПОЛУЧЕН ПЛАТЕЖ!")
    print(f"   User ID: {user_id}")
    print(f"   Payload: {payment_info.invoice_payload}")
    print("=" * 60)

    # Извлекаем ID платежа
    try:
        payment_id = int(payment_info.invoice_payload.replace("payment_", ""))
        print(f"   Payment ID: {payment_id}")
    except Exception as e:
        print(f"❌ Ошибка парсинга payload: {e}")
        await message.answer("❌ Ошибка платежа")
        return

    # Обновляем статус платежа и получаем данные в виде словаря
    payment_data = update_payment_status(payment_id, "success")
    if not payment_data:
        print("❌ Платеж не найден в БД")
        await message.answer("❌ Платеж не найден")
        return

    print(f"   Тариф из БД: {payment_data['tariff']}")

    # Находим тариф
    tariff_key = payment_data['tariff']
    tariff = config.TARIFFS.get(tariff_key)
    if not tariff:
        print(f"❌ Неизвестный тариф: {tariff_key}")
        await message.answer("❌ Неизвестный тариф")
        return

    print(f"   Тариф: {tariff['name']}, дней: {tariff['days']}")

    # Отправляем сообщение о начале активации
    await message.answer(
        f"✅ <b>Оплата получена!</b>\n\n"
        f"Активируем подписку...",
        parse_mode="HTML"
    )

    # Активируем подписку
    print("🔄 Вызываем activate_subscription...")
    success = await activate_subscription(user_id, tariff_key, tariff)
    print(f"🔄 Результат: {success}")

    if success:
        sub_url = await panel_api.get_subscription_url(f"user_{user_id}")
        await message.answer(
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"Тариф: {tariff['name']}\n"
            f"Срок: {tariff['days']} дней\n\n"
            f"🔗 <b>Ваша ссылка:</b>\n"
            f"<code>{sub_url}</code>",
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