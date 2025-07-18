from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import SUBSCRIPTION_PRICE


def get_payment_keyboard(payment_id: str, confirmation_url: str) -> InlineKeyboardMarkup:
    """Клавиатура для оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Оплатить",
            url=confirmation_url
        )],
        [InlineKeyboardButton(
            text="✅ Проверить оплату",
            callback_data=f"check_payment:{payment_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=f"cancel_payment:{payment_id}"
        )]
    ])


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления подпиской"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Оплатить подписку",
            callback_data="pay_subscription"
        )],
        [InlineKeyboardButton(
            text="📊 Статус подписки",
            callback_data="check_status"
        )],
        [InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="help"
        )]
    ])


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админская клавиатура"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton(text="📝 Логи", callback_data="admin_logs")
        ]
    ])


def get_confirmation_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да",
                callback_data=f"confirm:{action}:{data}"
            ),
            InlineKeyboardButton(
                text="❌ Нет", 
                callback_data="cancel_action"
            )
        ]
    ])


def get_user_management_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура управления пользователем"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Информация",
                callback_data=f"user_info:{user_id}"
            ),
            InlineKeyboardButton(
                text="⏰ Продлить",
                callback_data=f"extend_user:{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Заблокировать",
                callback_data=f"ban_user:{user_id}"
            ),
            InlineKeyboardButton(
                text="💰 Возврат",
                callback_data=f"refund_user:{user_id}"
            )
        ],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="admin_users"
        )]
    ])


def get_payment_status_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура статуса платежа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔄 Обновить статус",
            callback_data=f"refresh_payment:{payment_id}"
        )],
        [InlineKeyboardButton(
            text="📞 Поддержка",
            callback_data="support"
        )]
    ])


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура помощи"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Как оплатить?",
            callback_data="help_payment"
        )],
        [InlineKeyboardButton(
            text="🔧 Проблемы с доступом",
            callback_data="help_access"
        )],
        [InlineKeyboardButton(
            text="💰 Возврат средств",
            callback_data="help_refund"
        )],
        [InlineKeyboardButton(
            text="📞 Связаться с поддержкой",
            callback_data="support"
        )]
    ])


def get_back_keyboard(callback_data: str = "start") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=callback_data
        )]
    ])