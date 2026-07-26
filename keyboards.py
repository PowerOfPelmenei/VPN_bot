from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Мой статус", callback_data="status")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить ссылку", callback_data="refresh")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Купить подписку", callback_data="buy")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
    )

    return builder.as_markup()


def get_tariff_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с тарифами"""
    from config import TARIFFS

    builder = InlineKeyboardBuilder()

    for key, tariff in TARIFFS.items():
        if tariff["price"] == 0:
            label = f"🎁 {tariff['name']} - Бесплатно"
        else:
            label = f"💎 {tariff['name']} - {tariff['price']} ⭐"

        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"tariff_{key}")
        )

    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    return builder.as_markup()


def get_subscription_info_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для информации о подписке"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🔄 Обновить ссылку", callback_data="refresh"),
        InlineKeyboardButton(text="💎 Продлить", callback_data="buy")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель (для будущего использования)"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )

    return builder.as_markup()