import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from services.subscription_service import subscription_service
from services.notification_service import notification_service
from bot.keyboards.inline import get_subscription_keyboard, get_help_keyboard

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
                f"📢 Канал: {message.bot.get('channel_id', '@channel')}\n\n"
                f"Используйте /status для подробной информации",
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
        else:
            # Отправляем приветственное сообщение
            await notification_service.send_welcome_message(user)
        
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
        await notification_service.send_help_message(message.from_user.id, "general")
        logger.info(f"Пользователь {message.from_user.id} запросил справку")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")
        await message.answer("❌ Ошибка получения справки")


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    try:
        await notification_service.send_help_message(callback.from_user.id, "general")
        await callback.answer("📖 Справка отправлена!")
        
    except Exception as e:
        logger.error(f"Ошибка в callback help: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("help_"))
async def help_specific_callback(callback: CallbackQuery):
    """Обработчик конкретных типов справки"""
    try:
        help_type = callback.data.split("_", 1)[1]
        await notification_service.send_help_message(callback.from_user.id, help_type)
        await callback.answer("📖 Справка отправлена!")
        
    except Exception as e:
        logger.error(f"Ошибка в specific help callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    """Обработчик кнопки поддержки"""
    try:
        await notification_service.send_support_message(callback.from_user.id)
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