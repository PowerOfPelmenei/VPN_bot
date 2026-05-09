# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from config import TEST_DAYS

def get_main_keyboard():
    """Главная Reply-клавиатура"""
    buttons = [
        [KeyboardButton(text="📋 Моя подписка")],
        [KeyboardButton(text="🛒 Купить"), KeyboardButton(text="🔗 Ссылки")],
        [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="❓ Поддержка")]
    ]
    if TEST_DAYS:
        buttons.append([KeyboardButton(text="🧪 Тестовая подписка")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_buy_keyboard():
    """Инлайн-клавиатура для выбора периода подписки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц – 300⭐", callback_data="buy_1")],
        [InlineKeyboardButton(text="3 месяца – 600⭐", callback_data="buy_3")],
        [InlineKeyboardButton(text="Отмена", callback_data="buy_cancel")]
    ])

def get_account_keyboard():
    """Инлайн-клавиатура в личном кабинете"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Получить ссылки", callback_data="get_links")],
        [InlineKeyboardButton(text="📖 Инструкция по подключению", callback_data="instructions")],
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="renew")]
    ])