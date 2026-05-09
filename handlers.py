# handlers.py
import asyncio
import logging
import time
import uuid
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import LabeledPrice, PreCheckoutQuery

from config import PRICES, DAYS_MAP, TEST_DAYS, FREE_TRIAL_DAYS, ADMIN_IDS, INBOUND_REMARKS
from database import (
    get_user, create_user, mark_free_trial_used, add_payment,
    is_reward_given, mark_reward_given, update_subscription_end,
    get_referrals_count
)
from panel_api import create_or_update_subscription, get_client_link
from keyboards import get_main_keyboard, get_buy_keyboard, get_account_keyboard


class BuyStates(StatesGroup):
    choosing_period = State()

# ----- Команда /start -----
async def cmd_start(message: types.Message):
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
        except:
            pass

    user_id = message.from_user.id
    username = message.from_user.username
    existing = get_user(user_id)
    if not existing:
        create_user(user_id, username, referrer_id)
        text = "🎉 Добро пожаловать! Вы зарегистрированы.\n"
        if referrer_id and referrer_id != user_id:
            text += f"✅ Вы были приглашены пользователем {referrer_id}.\n"
    else:
        text = "👋 С возвращением!\n"

    text += "\nИспользуйте кнопки меню для управления подпиской."
    await message.answer(text, reply_markup=get_main_keyboard())

# ----- Команда /my (личный кабинет) -----
async def cmd_my(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("❌ Сначала /start")
        return
    sub_end_ms = user['subscription_end']
    now_ms = int(time.time() * 1000)
    active = sub_end_ms > now_ms
    if active:
        days_left = (sub_end_ms - now_ms) // (86400 * 1000)
        expiry_date = datetime.fromtimestamp(sub_end_ms / 1000).strftime("%d.%m.%Y %H:%M")
        status = f"✅ Активна до **{expiry_date}**\n📅 Осталось дней: {days_left}"
    else:
        status = "❌ Не активна"

    text = f"📊 **Ваш личный кабинет**\n\nСтатус подписки: {status}\nТариф: Безлимит\n\nВыберите действие:"
    await message.answer(text, parse_mode="Markdown", reply_markup=get_account_keyboard())

# ----- Команда /links -----
async def cmd_links(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or user['subscription_end'] <= int(time.time() * 1000):
        await message.answer("❌ Нет активной подписки.")
        return
    try:
        base_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{user_id}"))
        links = {}
        for remark in INBOUND_REMARKS:
            link = get_client_link(remark, base_uuid, user_id)
            links[remark] = link

        text = "🔗 *Ваши конфигурации для подключения*\n\n"
        text += "⚠️ *Как использовать:*\n• Нажмите на ссылку (на телефоне) — откроется VPN-клиент.\n• На компьютере — скопируйте ссылку и вставьте вручную.\n\n"
        for proto, link in links.items():
            text += f"*{proto}*\n`{link}`\n\n"
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ----- Команда /referral -----
async def cmd_referral(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("❌ /start")
        return
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    count = get_referrals_count(user_id)
    await message.answer(f"👥 **Реферальная программа**\n\nПриглашайте друзей -> +30 дней за каждого купившего.\nВаша ссылка:\n`{ref_link}`\n\nПриглашено: {count}", parse_mode="Markdown")

# ----- Команда /buy -----
async def cmd_buy(message: types.Message, state: FSMContext):
    await state.set_state(BuyStates.choosing_period)
    await message.answer("🛒 Выберите период подписки:", reply_markup=get_buy_keyboard())

# ----- Callback обработчики -----
async def process_buy_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data
    if data == "buy_cancel":
        await state.clear()
        await callback.message.edit_text("❌ Покупка отменена.")
        await callback.answer()
        return

    months = int(data.split("_")[1])
    amount = PRICES[months]
    payment_id = f"pay_{user_id}_{int(time.time())}"
    add_payment(payment_id, user_id, amount, months, "pending")
    prices = [LabeledPrice(label=f"VPN подписка {months} мес.", amount=amount)]
    await callback.bot.send_invoice(
        chat_id=user_id,
        title="VPN подписка",
        description=f"Доступ ко всем протоколам на {months} месяц(ев). Безлимитный трафик.",
        payload=payment_id,
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="vpn_subscription"
    )
    await callback.answer()
    await state.clear()

async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

async def successful_payment_handler(message: types.Message):
    payment = message.successful_payment
    payment_id = payment.invoice_payload
    user_id = message.from_user.id
    # получение months из БД
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT months FROM payments WHERE payment_id = ?", (payment_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        await message.answer("❌ Ошибка: не найден платёж.")
        return
    months = row[0]
    days = DAYS_MAP[months]

    # обновить статус платежа
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE payments SET status = 'paid' WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()

    await message.answer("🔄 Создаю VPN-доступ...")
    try:
        links = await create_or_update_subscription(user_id, days)
        text = "✅ **Оплата прошла успешно!**\n\nВаши конфигурации:\n\n"
        for proto, link in links.items():
            text += f"🔹 **{proto}**\n`{link}`\n\n"
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка после оплаты: {e}")
        await message.answer(f"❌ Ошибка: {e}")

    # Реферальная программа
    user = get_user(user_id)
    referrer_id = user.get('referrer_id')
    if referrer_id and not is_reward_given(referrer_id, user_id):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM payments WHERE user_id = ? AND status = 'paid'", (user_id,))
        previous_payment = cur.fetchone()
        conn.close()
        if not previous_payment:
            referrer = get_user(referrer_id)
            if referrer:
                current_end_ms = referrer['subscription_end']
                now_ms = int(time.time() * 1000)
                new_end_ms = max(current_end_ms, now_ms) + 30 * 86400 * 1000
                update_subscription_end(referrer_id, new_end_ms)
                mark_reward_given(referrer_id, user_id)
                try:
                    await message.bot.send_message(referrer_id,
                                           f"🎁 Ваш друг @{message.from_user.username} купил подписку!\nВы получили +30 дней бесплатно!")
                except:
                    pass

# ----- Тестовая подписка (опционально) -----
async def cmd_test(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(user_id, message.from_user.username)
        user = get_user(user_id)

    if user['subscription_end'] > int(time.time() * 1000):
        expiry_date = datetime.fromtimestamp(user['subscription_end'] / 1000).strftime("%d.%m.%Y %H:%M")
        await message.answer(f"ℹ️ У вас уже есть активная подписка до **{expiry_date}**\nИспользуйте /links для получения ссылок или /buy для продления.", parse_mode="Markdown")
        return

    await message.answer("🔄 Выдаю ТЕСТОВУЮ подписку на 30 дней...")
    try:
        links = await create_or_update_subscription(user_id, TEST_DAYS, ignore_trial_flag=True)
        text = "✅ **Тестовая подписка активирована!**\n\n🗓 Срок действия: 30 дней\n\nВаши конфигурации:\n\n"
        for proto, link in links.items():
            text += f"🔹 **{proto}**\n`{link}`\n\n"
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка test: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

# ----- Админ-команды -----
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE subscription_end > ?", (int(time.time() * 1000),))
    active_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payments WHERE status='paid'")
    total_payments = cur.fetchone()[0]
    conn.close()
    text = f"📊 **Статистика**\n\n👥 Всего пользователей: {total_users}\n✅ Активных подписок: {active_users}\n💰 Оплат (всего): {total_payments}"
    await message.answer(text, parse_mode="Markdown")

async def cmd_broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("❌ Укажите текст рассылки после /broadcast")
        return
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    conn.close()
    sent = 0
    for (user_id,) in users:
        try:
            await message.bot.send_message(user_id, text, parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ Рассылка завершена. Отправлено {sent} из {len(users)} пользователей.")

# ----- Прочие команды -----
async def cmd_support(message: types.Message):
    await message.answer("📞 Поддержка: @your_support")

async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.")

async def inline_links(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_links(callback.message)

async def inline_instructions(callback: types.CallbackQuery):
    await callback.answer()
    text = "📖 **Инструкция по подключению**\n\n1. Скачайте VPN-клиент: [NekoBox](https://github.com/MatsuriDayo/NekoBoxForAndroid/releases) (Android), [V2RayNG](https://github.com/2dust/v2rayNG/releases) (Android), [Hiddify](https://hiddify.com/) (iOS/Android/Windows)\n2. Скопируйте ссылку из команды /links\n3. Откройте приложение → Добавить конфигурацию → Импорт из буфера обмена.\n4. Подключитесь."
    await callback.message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

async def inline_renew(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_buy(callback.message, state)

# ----- Регистрация хендлеров -----
def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_my, Command("my"))
    dp.message.register(cmd_links, Command("links"))
    dp.message.register(cmd_referral, Command("referral"))
    dp.message.register(cmd_buy, Command("buy"))
    dp.message.register(cmd_test, Command("test"))
    dp.message.register(cmd_admin, Command("admin"))
    dp.message.register(cmd_broadcast, Command("broadcast"))
    dp.message.register(cmd_support, Command("support"))
    dp.message.register(cmd_cancel, Command("cancel"))

    dp.callback_query.register(process_buy_callback, lambda c: c.data.startswith("buy_"))
    dp.callback_query.register(inline_links, lambda c: c.data == "get_links")
    dp.callback_query.register(inline_instructions, lambda c: c.data == "instructions")
    dp.callback_query.register(inline_renew, lambda c: c.data == "renew")

    dp.pre_checkout_query.register(pre_checkout_handler)
    dp.message.register(successful_payment_handler, lambda m: m.successful_payment is not None)