import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from services.subscription_service import subscription_service
from services.telegram_service import telegram_service
from bot.keyboards.inline import get_subscription_keyboard, get_back_keyboard
from config.settings import CHANNEL_ID

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("status"))
async def status_command(message: Message):
    """Обработчик команды /status"""
    try:
        user_id = message.from_user.id
        
        # Получаем статус подписки
        status_info = await subscription_service.get_subscription_status(user_id)
        
        if not status_info:
            await message.answer(
                "❌ Информация о подписке не найдена.\n\n"
                "Возможно, вы еще не использовали команду /start",
                reply_markup=get_subscription_keyboard()
            )
            return
        
        # Формируем сообщение о статусе
        if status_info["is_active"]:
            status_emoji = "✅"
            status_text = "Активна"
            
            # Проверяем, находится ли пользователь в канале
            in_channel = await telegram_service.check_user_in_channel(user_id)
            channel_status = "✅ В канале" if in_channel else "❌ Не в канале"
            
            message_text = f"""
{status_emoji} <b>Статус подписки: {status_text}</b>

📅 Действует до: {status_info['end_date'].strftime('%d.%m.%Y в %H:%M')}
⏰ Осталось дней: {status_info['days_left']}
📢 Канал: {CHANNEL_ID}
👤 Статус в канале: {channel_status}

💰 Всего платежей: {status_info['total_payments']}
📅 Дата регистрации: {status_info['created_at'].strftime('%d.%m.%Y') if status_info['created_at'] else 'Неизвестно'}
            """.strip()
            
            # Добавляем предупреждение если подписка скоро истечет
            if status_info['days_left'] <= 3:
                message_text += f"\n\n⚠️ <b>Внимание!</b> Подписка истекает через {status_info['days_left']} дн. Продлите заранее!"
                
        else:
            status_emoji = "❌"
            
            if status_info['status'] == 'expired':
                status_text = "Истекла"
                if status_info['end_date']:
                    message_text = f"""
{status_emoji} <b>Статус подписки: {status_text}</b>

📅 Истекла: {status_info['end_date'].strftime('%d.%m.%Y в %H:%M')}
📢 Канал: {CHANNEL_ID}
👤 Доступ: Отсутствует

💰 Всего платежей: {status_info['total_payments']}

Используйте /pay для продления подписки
                    """.strip()
                else:
                    message_text = f"""
{status_emoji} <b>Статус подписки: Отсутствует</b>

📢 Канал: {CHANNEL_ID}
👤 Доступ: Отсутствует

Используйте /pay для оформления подписки
                    """.strip()
                    
            elif status_info['status'] == 'trial':
                status_text = "Пробный период"
                message_text = f"""
🔶 <b>Статус подписки: {status_text}</b>

📅 Действует до: {status_info['end_date'].strftime('%d.%m.%Y в %H:%M')}
⏰ Осталось дней: {status_info['days_left']}
📢 Канал: {CHANNEL_ID}

💡 После окончания пробного периода необходимо оплатить подписку
                """.strip()
                
            elif status_info['status'] == 'suspended':
                status_text = "Приостановлена"
                message_text = f"""
⏸️ <b>Статус подписки: {status_text}</b>

📢 Канал: {CHANNEL_ID}
👤 Доступ: Отсутствует

Обратитесь в поддержку для разблокировки
                """.strip()
            else:
                status_text = "Неопределен"
                message_text = f"""
❓ <b>Статус подписки: {status_text}</b>

Обратитесь в поддержку для уточнения статуса
                """.strip()
        
        await message.answer(
            message_text,
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {user_id} проверил статус подписки: {status_info['status']}")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /status: {e}")
        await message.answer(
            "❌ Ошибка получения статуса подписки. Попробуйте позже.",
            reply_markup=get_subscription_keyboard()
        )


@router.callback_query(F.data == "check_status")
async def check_status_callback(callback: CallbackQuery):
    """Обработчик кнопки проверки статуса"""
    try:
        # Имитируем команду /status
        message = callback.message
        message.from_user = callback.from_user
        await status_command(message)
        await callback.answer("📊 Статус обновлен!")
        
    except Exception as e:
        logger.error(f"Ошибка в check_status callback: {e}")
        await callback.answer("❌ Ошибка получения статуса", show_alert=True)


@router.message(Command("info"))
async def info_command(message: Message):
    """Обработчик команды /info - общая информация"""
    try:
        # Получаем информацию о канале
        channel_info = await telegram_service.get_channel_info()
        
        if channel_info:
            member_count = channel_info.get("member_count", "Неизвестно")
            channel_title = channel_info.get("title", "Канал")
        else:
            member_count = "Неизвестно"
            channel_title = "Канал"
        
        message_text = f"""
ℹ️ <b>Информация о сервисе</b>

📢 <b>Канал:</b> {CHANNEL_ID}
🏷️ <b>Название:</b> {channel_title}
👥 <b>Участников:</b> {member_count}

💰 <b>Стоимость подписки:</b> {int(subscription_service.__dict__.get('subscription_price', 500))} руб/месяц
⏰ <b>Срок действия:</b> 30 дней

<b>Возможности подписки:</b>
• Полный доступ к контенту канала
• Мгновенная активация после оплаты
• Автоматическое управление доступом
• Техническая поддержка

<b>Способы оплаты:</b>
• Банковские карты (Visa, MasterCard, МИР)
• SberPay, YooMoney
• Другие способы через ЮKassa

Для оформления подписки используйте команду /pay
        """.strip()
        
        await message.answer(
            message_text,
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Пользователь {message.from_user.id} запросил общую информацию")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /info: {e}")
        await message.answer(
            "❌ Ошибка получения информации. Попробуйте позже.",
            reply_markup=get_subscription_keyboard()
        )


@router.message(Command("myid"))
async def myid_command(message: Message):
    """Обработчик команды /myid - показать свой ID"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        message_text = f"""
🆔 <b>Ваша информация</b>

👤 <b>ID:</b> <code>{user_id}</code>
📝 <b>Username:</b> @{username if username else 'не указан'}
👋 <b>Имя:</b> {first_name if first_name else 'не указано'}

💡 ID может потребоваться для обращения в поддержку
        """.strip()
        
        await message.answer(
            message_text,
            reply_markup=get_back_keyboard("start"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /myid: {e}")
        await message.answer("❌ Ошибка получения информации")


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)