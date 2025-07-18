import logging
from datetime import datetime, timedelta
from typing import List

from database.database import db
from database.models import User, SubscriptionStatus
from services.subscription_service import subscription_service
from services.notification_service import notification_service
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)


async def check_expired_subscriptions() -> dict:
    """
    Проверка и деактивация истекших подписок
    
    Returns:
        Словарь со статистикой проверки
    """
    try:
        logger.info("Начинаем проверку истекших подписок")
        
        # Получаем количество деактивированных подписок
        expired_count = await subscription_service.check_and_expire_subscriptions()
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "expired_count": expired_count,
            "status": "completed"
        }
        
        logger.info(f"Проверка завершена. Деактивировано подписок: {expired_count}")
        
        # Если были деактивированные подписки, уведомляем админов
        if expired_count > 0:
            await _notify_admins_about_expired(expired_count)
        
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка проверки истекших подписок: {e}")
        
        # Уведомляем админов об ошибке
        await _notify_admins_about_error("check_expired_subscriptions", str(e))
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }


async def send_expiration_reminders() -> dict:
    """
    Отправка напоминаний о скором истечении подписок
    
    Returns:
        Словарь со статистикой отправки
    """
    try:
        logger.info("Начинаем отправку напоминаний об истечении подписок")
        
        # Получаем пользователей с подписками, истекающими в ближайшие дни
        users_1_day = await _get_users_expiring_in_days(1)
        users_3_days = await _get_users_expiring_in_days(3)
        users_7_days = await _get_users_expiring_in_days(7)
        
        sent_count = 0
        
        # Отправляем напоминания для разных периодов
        for user in users_1_day:
            if await notification_service.send_subscription_reminder(user, 1):
                sent_count += 1
        
        for user in users_3_days:
            if await notification_service.send_subscription_reminder(user, 3):
                sent_count += 1
        
        for user in users_7_days:
            if await notification_service.send_subscription_reminder(user, 7):
                sent_count += 1
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "reminders_sent": sent_count,
            "users_1_day": len(users_1_day),
            "users_3_days": len(users_3_days),
            "users_7_days": len(users_7_days),
            "status": "completed"
        }
        
        logger.info(f"Напоминания отправлены. Всего: {sent_count}")
        
        # Уведомляем админов о результатах
        if sent_count > 0:
            await _notify_admins_about_reminders(stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка отправки напоминаний: {e}")
        
        # Уведомляем админов об ошибке
        await _notify_admins_about_error("send_expiration_reminders", str(e))
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }


async def _get_users_expiring_in_days(days: int) -> List[User]:
    """
    Получить пользователей с подписками, истекающими через указанное количество дней
    
    Args:
        days: Количество дней до истечения
        
    Returns:
        Список пользователей
    """
    try:
        # Вычисляем временные границы
        target_date = datetime.now() + timedelta(days=days)
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Здесь нужен более сложный SQL запрос, упрощенная версия:
        # В реальном проекте лучше добавить метод в Database класс
        
        users = []
        # Эту логику нужно доработать с правильными SQL запросами
        
        return users
        
    except Exception as e:
        logger.error(f"Ошибка получения пользователей с истечением через {days} дней: {e}")
        return []


async def check_subscription_renewals() -> dict:
    """
    Проверка возможности автоматического продления подписок
    
    Returns:
        Словарь со статистикой продлений
    """
    try:
        logger.info("Проверяем возможности автоматического продления")
        
        # Получаем пользователей с подписками, истекающими завтра
        users_expiring_tomorrow = await _get_users_expiring_in_days(1)
        
        renewed_count = 0
        failed_count = 0
        
        for user in users_expiring_tomorrow:
            # Проверяем, есть ли у пользователя сохраненная карта
            if user.yookassa_customer_id:
                # Здесь можно реализовать автоматическое списание
                # Пока что только логируем
                logger.info(f"Пользователь {user.user_id} может быть продлен автоматически")
                # success = await _attempt_auto_renewal(user)
                # if success:
                #     renewed_count += 1
                # else:
                #     failed_count += 1
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "eligible_users": len(users_expiring_tomorrow),
            "renewed_count": renewed_count,
            "failed_count": failed_count,
            "status": "completed"
        }
        
        logger.info(f"Проверка продлений завершена: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка проверки продлений: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }


async def cleanup_inactive_users() -> dict:
    """
    Очистка неактивных пользователей (не использовавших бота долгое время)
    
    Returns:
        Словарь со статистикой очистки
    """
    try:
        logger.info("Начинаем очистку неактивных пользователей")
        
        # Порог неактивности - 6 месяцев
        inactive_threshold = datetime.now() - timedelta(days=180)
        
        # Здесь нужен SQL запрос для поиска неактивных пользователей
        # Упрощенная версия:
        
        cleaned_count = 0
        
        # В реальной реализации:
        # 1. Найти пользователей без активности > 180 дней
        # 2. У которых нет активной подписки
        # 3. Удалить их данные или пометить как архивных
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "cleaned_count": cleaned_count,
            "threshold_date": inactive_threshold.isoformat(),
            "status": "completed"
        }
        
        logger.info(f"Очистка неактивных пользователей завершена: {cleaned_count}")
        return stats
        
    except Exception as e:
        logger.error(f"Ошибка очистки неактивных пользователей: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }


async def _notify_admins_about_expired(expired_count: int):
    """Уведомить админов о деактивированных подписках"""
    try:
        message = f"""
⚠️ <b>Деактивация подписок</b>

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}
👥 Деактивировано: {expired_count} подписок

Пользователи исключены из канала и уведомлены.
        """.strip()
        
        for admin_id in ADMIN_IDS:
            await notification_service.send_admin_notification(admin_id, message)
            
    except Exception as e:
        logger.error(f"Ошибка уведомления админов об истекших подписках: {e}")


async def _notify_admins_about_reminders(stats: dict):
    """Уведомить админов о результатах отправки напоминаний"""
    try:
        message = f"""
📢 <b>Напоминания об истечении подписок</b>

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}
📤 Отправлено напоминаний: {stats['reminders_sent']}

📊 <b>По периодам:</b>
• 1 день: {stats['users_1_day']} чел.
• 3 дня: {stats['users_3_days']} чел.  
• 7 дней: {stats['users_7_days']} чел.

Пользователи уведомлены о необходимости продления.
        """.strip()
        
        for admin_id in ADMIN_IDS:
            await notification_service.send_admin_notification(admin_id, message)
            
    except Exception as e:
        logger.error(f"Ошибка уведомления админов о напоминаниях: {e}")


async def _notify_admins_about_error(task_name: str, error_message: str):
    """Уведомить админов об ошибке в задаче"""
    try:
        message = f"""
❌ <b>Ошибка в фоновой задаче</b>

🔧 Задача: {task_name}
📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}
💬 Ошибка: {error_message}

Требуется проверка системы.
        """.strip()
        
        for admin_id in ADMIN_IDS:
            await notification_service.send_admin_notification(admin_id, message)
            
    except Exception as e:
        logger.error(f"Ошибка уведомления админов об ошибке: {e}")


# Экспортируемые функции для использования в планировщике
__all__ = [
    'check_expired_subscriptions',
    'send_expiration_reminders', 
    'check_subscription_renewals',
    'cleanup_inactive_users'
]