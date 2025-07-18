import logging
from typing import Optional
from datetime import datetime

from config.settings import CHANNEL_ID, SUBSCRIPTION_PRICE, MESSAGES
from database.models import User
from services.telegram_service import telegram_service
from bot.keyboards.inline import get_subscription_keyboard, get_help_keyboard

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений пользователям"""
    
    async def send_welcome_message(self, user: User) -> bool:
        """
        Отправить приветственное сообщение
        
        Args:
            user: Пользователь
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            message = MESSAGES['welcome'].format(
                channel_id=CHANNEL_ID,
                price=int(SUBSCRIPTION_PRICE)
            )
            
            keyboard = get_subscription_keyboard()
            
            return await telegram_service.send_message(
                user.user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки приветствия пользователю {user.user_id}: {e}")
            return False
    
    async def send_subscription_activated(self, user: User, invite_link: Optional[str] = None) -> bool:
        """
        Отправить уведомление об активации подписки
        
        Args:
            user: Пользователь
            invite_link: Ссылка для входа в канал
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            if invite_link:
                message = MESSAGES['payment_success'].format(
                    subscription_end=user.subscription_end.strftime('%d.%m.%Y %H:%M'),
                    invite_link=invite_link
                )
            else:
                message = f"""
✅ <b>Оплата прошла успешно!</b>

📅 Подписка активна до: {user.subscription_end.strftime('%d.%m.%Y %H:%M')}
📢 Канал: {CHANNEL_ID}

Обратитесь к администратору для получения доступа к каналу.

Спасибо за оплату! 🎉
                """.strip()
            
            return await telegram_service.send_message(
                user.user_id,
                message
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об активации {user.user_id}: {e}")
            return False
    
    async def send_subscription_expired(self, user: User) -> bool:
        """
        Отправить уведомление об истечении подписки
        
        Args:
            user: Пользователь
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            message = MESSAGES['subscription_expired']
            keyboard = get_subscription_keyboard()
            
            return await telegram_service.send_message(
                user.user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об истечении {user.user_id}: {e}")
            return False
    
    async def send_subscription_extended(self, user: User, days: int, reason: str) -> bool:
        """
        Отправить уведомление о продлении подписки
        
        Args:
            user: Пользователь
            days: Количество дней продления
            reason: Причина продления
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            reason_text = {
                "payment": "оплаты",
                "manual": "администратором",
                "bonus": "бонуса",
                "refund": "компенсации"
            }.get(reason, reason)
            
            message = f"""
✅ <b>Подписка продлена!</b>

📅 Активна до: {user.subscription_end.strftime('%d.%m.%Y %H:%M')}
⏰ Продлена на: {days} дней
💡 Причина: {reason_text}

Спасибо за то, что с нами! 🎉
            """.strip()
            
            return await telegram_service.send_message(
                user.user_id,
                message
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о продлении {user.user_id}: {e}")
            return False
    
    async def send_subscription_cancelled(self, user: User, reason: str) -> bool:
        """
        Отправить уведомление об отмене подписки
        
        Args:
            user: Пользователь
            reason: Причина отмены
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            reason_text = {
                "user_request": "по вашему запросу",
                "payment_failed": "из-за неуспешной оплаты",
                "violation": "за нарушение правил",
                "refund": "в связи с возвратом средств"
            }.get(reason, reason)
            
            message = f"""
❌ <b>Подписка отменена</b>

💡 Причина: {reason_text}
📢 Доступ к каналу {CHANNEL_ID} приостановлен

Для возобновления подписки используйте команду /pay
            """.strip()
            
            keyboard = get_subscription_keyboard()
            
            return await telegram_service.send_message(
                user.user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об отмене {user.user_id}: {e}")
            return False
    
    async def send_payment_failed(self, user_id: int, reason: str = "") -> bool:
        """
        Отправить уведомление о неуспешной оплате
        
        Args:
            user_id: ID пользователя
            reason: Причина неудачи
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            message = MESSAGES['payment_failed']
            if reason:
                message += f"\n\nПричина: {reason}"
            
            keyboard = get_subscription_keyboard()
            
            return await telegram_service.send_message(
                user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о неуспешной оплате {user_id}: {e}")
            return False
    
    async def send_subscription_reminder(self, user: User, days_left: int) -> bool:
        """
        Отправить напоминание о скором истечении подписки
        
        Args:
            user: Пользователь
            days_left: Дней до истечения
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            if days_left <= 1:
                emoji = "🚨"
                urgency = "срочно"
            elif days_left <= 3:
                emoji = "⚠️"
                urgency = "скоро"
            else:
                emoji = "ℹ️"
                urgency = ""
            
            message = f"""
{emoji} <b>Напоминание о подписке</b>

📅 Ваша подписка истекает {urgency}: {user.subscription_end.strftime('%d.%m.%Y в %H:%M')}
⏰ Осталось дней: {days_left}

Продлите подписку, чтобы не потерять доступ к каналу!
            """.strip()
            
            keyboard = get_subscription_keyboard()
            
            return await telegram_service.send_message(
                user.user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания {user.user_id}: {e}")
            return False
    
    async def send_admin_notification(self, admin_id: int, message: str) -> bool:
        """
        Отправить уведомление администратору
        
        Args:
            admin_id: ID администратора
            message: Сообщение
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            formatted_message = f"""
🔔 <b>Уведомление администратора</b>

⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

{message}
            """.strip()
            
            return await telegram_service.send_message(
                admin_id,
                formatted_message
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
            return False
    
    async def send_support_message(self, user_id: int) -> bool:
        """
        Отправить сообщение с контактами поддержки
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
            message = """
📞 <b>Поддержка</b>

Если у вас возникли проблемы, обратитесь к нашей службе поддержки:

📧 Email: support@example.com
💬 Telegram: @support_bot
🕐 Время работы: 9:00-18:00 (МСК)

Мы поможем решить любые вопросы!
            """.strip()
            
            keyboard = get_help_keyboard()
            
            return await telegram_service.send_message(
                user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки контактов поддержки {user_id}: {e}")
            return False
    
    async def send_help_message(self, user_id: int, help_type: str = "general") -> bool:
        """
        Отправить справочное сообщение
        
        Args:
            user_id: ID пользователя
            help_type: Тип справки
            
        Returns:
            True если отправлено, False если ошибка
        """
        try:
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
                """.strip(),
                
                "general": """
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
            }
            
            message = messages.get(help_type, messages["general"])
            keyboard = get_help_keyboard()
            
            return await telegram_service.send_message(
                user_id,
                message,
                keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки справки {user_id}: {e}")
            return False


# Глобальный экземпляр сервиса
notification_service = NotificationService()