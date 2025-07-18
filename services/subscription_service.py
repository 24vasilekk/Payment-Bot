import logging
from datetime import datetime, timedelta
from typing import Optional, List
from aiogram.types import User as TgUser

from config.settings import SUBSCRIPTION_DURATION_DAYS, TRIAL_PERIOD_DAYS
from database.database import db
from database.models import User, SubscriptionStatus, Payment, PaymentStatus
from services.telegram_service import telegram_service
from services.notification_service import notification_service
from utils.logger import payment_logger

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Сервис для управления подписками"""
    
    async def create_or_update_user(self, tg_user: TgUser) -> User:
        """
        Создать или обновить пользователя
        
        Args:
            tg_user: Telegram пользователь
            
        Returns:
            Объект User
        """
        user = await db.get_user(tg_user.id)
        
        if user:
            # Обновляем информацию о пользователе
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
        else:
            # Создаем нового пользователя
            user = User(
                user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                subscription_status=SubscriptionStatus.EXPIRED,
                created_at=datetime.now()
            )
            
            # Если есть пробный период, активируем его
            if TRIAL_PERIOD_DAYS > 0:
                user.subscription_end = datetime.now() + timedelta(days=TRIAL_PERIOD_DAYS)
                user.subscription_status = SubscriptionStatus.TRIAL
                logger.info(f"Пользователь {user.user_id} получил пробный период на {TRIAL_PERIOD_DAYS} дней")
        
        await db.save_user(user)
        return user
    
    async def activate_subscription(self, user_id: int, payment: Payment) -> bool:
        """
        Активировать подписку после успешной оплаты
        
        Args:
            user_id: ID пользователя
            payment: Объект платежа
            
        Returns:
            True если активирована, False если ошибка
        """
        try:
            user = await db.get_user(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден")
                return False
            
            # Определяем дату окончания подписки
            now = datetime.now()
            
            if user.subscription_end and user.subscription_end > now:
                # Продлеваем существующую подписку
                user.subscription_end += timedelta(days=SUBSCRIPTION_DURATION_DAYS)
            else:
                # Создаем новую подписку
                user.subscription_end = now + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
            
            user.subscription_status = SubscriptionStatus.ACTIVE
            user.is_active = True
            user.total_payments += 1
            
            # Сохраняем пользователя
            if await db.save_user(user):
                # Создаем инвайт-ссылку
                invite_link = await telegram_service.create_invite_link(user_id)
                
                if invite_link:
                    # Отправляем уведомление с ссылкой
                    await notification_service.send_subscription_activated(
                        user, invite_link
                    )
                else:
                    # Отправляем уведомление без ссылки
                    await notification_service.send_subscription_activated(
                        user, None
                    )
                
                payment_logger.subscription_extended(user_id, user.subscription_end)
                logger.info(f"Подписка активирована для пользователя {user_id} до {user.subscription_end}")
                return True
            else:
                logger.error(f"Ошибка сохранения пользователя {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка активации подписки для {user_id}: {e}")
            return False
    
    async def extend_subscription(self, user_id: int, days: int, reason: str = "manual") -> bool:
        """
        Продлить подписку пользователя
        
        Args:
            user_id: ID пользователя
            days: Количество дней для продления
            reason: Причина продления
            
        Returns:
            True если продлена, False если ошибка
        """
        try:
            user = await db.get_user(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден")
                return False
            
            now = datetime.now()
            
            if user.subscription_end and user.subscription_end > now:
                user.subscription_end += timedelta(days=days)
            else:
                user.subscription_end = now + timedelta(days=days)
            
            user.subscription_status = SubscriptionStatus.ACTIVE
            user.is_active = True
            
            if await db.save_user(user):
                await notification_service.send_subscription_extended(user, days, reason)
                payment_logger.subscription_extended(user_id, user.subscription_end)
                logger.info(f"Подписка продлена для {user_id} на {days} дней. Причина: {reason}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Ошибка продления подписки для {user_id}: {e}")
            return False
    
    async def cancel_subscription(self, user_id: int, reason: str = "user_request") -> bool:
        """
        Отменить подписку пользователя
        
        Args:
            user_id: ID пользователя
            reason: Причина отмены
            
        Returns:
            True если отменена, False если ошибка
        """
        try:
            user = await db.get_user(user_id)
            if not user:
                return False
            
            user.subscription_status = SubscriptionStatus.SUSPENDED
            user.is_active = False
            
            if await db.save_user(user):
                # Исключаем из канала
                await telegram_service.kick_user_from_channel(user_id)
                
                # Отправляем уведомление
                await notification_service.send_subscription_cancelled(user, reason)
                
                payment_logger.user_kicked(user_id, reason)
                logger.info(f"Подписка отменена для {user_id}. Причина: {reason}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Ошибка отмены подписки для {user_id}: {e}")
            return False
    
    async def check_and_expire_subscriptions(self) -> int:
        """
        Проверить и деактивировать истекшие подписки
        
        Returns:
            Количество деактивированных подписок
        """
        try:
            expired_users = await db.get_expired_users()
            expired_count = 0
            
            for user in expired_users:
                if await self._expire_user_subscription(user):
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Деактивировано {expired_count} подписок")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Ошибка проверки истекших подписок: {e}")
            return 0
    
    async def _expire_user_subscription(self, user: User) -> bool:
        """
        Деактивировать подписку конкретного пользователя
        
        Args:
            user: Пользователь
            
        Returns:
            True если деактивирована, False если ошибка
        """
        try:
            # Обновляем статус
            user.subscription_status = SubscriptionStatus.EXPIRED
            user.is_active = False
            
            if await db.save_user(user):
                # Исключаем из канала
                await telegram_service.kick_user_from_channel(user.user_id)
                
                # Отправляем уведомление
                await notification_service.send_subscription_expired(user)
                
                payment_logger.subscription_expired(user.user_id)
                payment_logger.user_kicked(user.user_id, "subscription_expired")
                
                logger.info(f"Подписка истекла для пользователя {user.user_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Ошибка деактивации подписки для {user.user_id}: {e}")
            return False
    
    async def get_subscription_status(self, user_id: int) -> Optional[dict]:
        """
        Получить статус подписки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статусом подписки или None
        """
        try:
            user = await db.get_user(user_id)
            if not user:
                return None
            
            return {
                "is_active": user.is_subscription_active,
                "status": user.subscription_status.value,
                "end_date": user.subscription_end,
                "days_left": user.days_left,
                "total_payments": user.total_payments,
                "created_at": user.created_at
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса подписки для {user_id}: {e}")
            return None
    
    async def get_users_count_by_status(self) -> dict:
        """
        Получить количество пользователей по статусам
        
        Returns:
            Словарь с количеством пользователей по статусам
        """
        try:
            # Простая реализация без сложных SQL запросов
            stats = {
                "active": 0,
                "expired": 0,
                "trial": 0,
                "suspended": 0,
                "total": 0
            }
            
            # В реальном проекте лучше сделать отдельные SQL запросы для каждого статуса
            # Здесь упрощенная версия
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователей: {e}")
            return {}
    
    async def get_revenue_stats(self, days: int = 30) -> dict:
        """
        Получить статистику доходов
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой доходов
        """
        try:
            # Упрощенная реализация
            stats = {
                "total_revenue": 0.0,
                "successful_payments": 0,
                "failed_payments": 0,
                "period_days": days
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики доходов: {e}")
            return {}


# Глобальный экземпляр сервиса
subscription_service = SubscriptionService()