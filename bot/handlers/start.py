import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from services.subscription_service import subscription_service
from services.notification_service import notification_service
from bot.keyboards.inline import get_subscription_keyboard, get_help_keyboard
from config.settings import CHANNEL_ID, SUBSCRIPTION_PRICE, MESSAGES

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def start_command(message: Message):
    """Обработчик команды /start"""
    try:
        # Создаем или обновляем пользователя
        user = await subscription_service.create_or_update_user(message.from_user)
        
        # Проверяем статус подписки
        if user.is_subscription_active:
            await message.answer(
                f"✅ <b>Добро пожаловать обратно!</b>\n\n"
                f"📅 Ваша подписка активна до: {user.subscription_end.strftime('%d.%m.%Y %H:%M')}\n"
                f"⏰ Осталось дней: {user.days_left}\n\n"
                f"📢 Канал: {CHANNEL_ID}\n\n"
                f"Используйте /status для подробной информации",
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
        else:
            # Отправляем приветственное сообщение напрямую
            welcome_message = MESSAGES['welcome'].format(
                channel_id=CHANNEL_ID,
                price=int(SUBSCRIPTION_PRICE)
            )
            
            await message.answer(
                welcome_message,
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
        
        logger.info(f"Пользователь {user.user_id} ({user.full_name}) использовал команду /start")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже или обратитесь в поддержку.",
            reply_markup=get_subscription_keyboard()
        )


@router.message(Command("help"))
async def help_command(message: Message):
    """Обработчик команды /help"""
    try:
        help_message = """
❓ <b>Справка по боту</b>

<b>Основные команды:</b>
/start - Начало работы
/pay - Оплата подписки
/status - Статус подписки
/help - Эта справка

<b>Как это работает:</b>
1. Оплачиваете подписку
2. Получаете ссылку на канал
3. Присоединяетесь к каналу
4. Наслаждаетесь контентом!

<b>Поддержка:</b> @support_bot
        """.strip()
        
        await message.answer(
            help_message,
            reply_markup=get_help_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {message.from_user.id} запросил справку")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")
        await message.answer("❌ Ошибка получения справки")


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    try:
        help_message = """
❓ <b>Справка по боту</b>

<b>Основные команды:</b>
/start - Начало работы
/pay - Оплата подписки
/status - Статус подписки
/help - Эта справка

<b>Как это работает:</b>
1. Оплачиваете подписку
2. Получаете ссылку на канал
3. Присоединяетесь к каналу
4. Наслаждаетесь контентом!

<b>Поддержка:</b> @support_bot
        """.strip()
        
        await callback.message.answer(
            help_message,
            reply_markup=get_help_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("📖 Справка отправлена!")
        
    except Exception as e:
        logger.error(f"Ошибка в callback help: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("help_"))
async def help_specific_callback(callback: CallbackQuery):
    """Обработчик конкретных типов справки"""
    try:
        help_type = callback.data.split("_", 1)[1]
        
        messages = {
            "payment": """
💳 <b>Как оплатить подписку?</b>

1. Используйте команду /pay
2. Нажмите кнопку "💳 Оплатить"
3. Выберите способ оплаты
4. Следуйте инструкциям
5. После оплаты нажмите "✅ Проверить оплату"

Доступ откроется автоматически!
            """.strip(),
            
            "access": """
🔧 <b>Проблемы с доступом?</b>

Возможные причины:
• Подписка истекла
• Ссылка-приглашение устарела
• Вы покинули канал

Решения:
• Проверьте статус: /status
• Продлите подписку: /pay
• Обратитесь в поддержку

Мы поможем!
            """.strip(),
            
            "refund": """
💰 <b>Возврат средств</b>

Условия возврата:
• В течение 14 дней с момента оплаты
• При технических проблемах
• По решению администрации

Для возврата обратитесь в поддержку с указанием:
• ID платежа
• Причины возврата
• Контактных данных
            """.strip()
        }
        
        message = messages.get(help_type, messages.get("payment"))
        
        await callback.message.answer(
            message,
            reply_markup=get_help_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("📖 Справка отправлена!")
        
    except Exception as e:
        logger.error(f"Ошибка в specific help callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    """Обработчик кнопки поддержки"""
    try:
        support_message = """
📞 <b>Поддержка</b>

Если у вас возникли проблемы, обратитесь к нашей службе поддержки:

📧 Email: support@example.com
💬 Telegram: @support_bot
🕐 Время работы: 9:00-18:00 (МСК)

Мы поможем решить любые вопросы!
        """.strip()
        
        await callback.message.answer(
            support_message,
            reply_markup=get_help_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("📞 Контакты поддержки отправлены!")
        
    except Exception as e:
        logger.error(f"Ошибка в support callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_action")
async def cancel_action_callback(callback: CallbackQuery):
    """Обработчик отмены действия"""
    try:
        await callback.message.edit_text(
            "❌ Действие отменено",
            reply_markup=get_subscription_keyboard()
        )
        await callback.answer("Отменено")
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_action callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)