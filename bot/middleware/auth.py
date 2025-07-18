import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, Message, CallbackQuery

from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    """Фильтр для проверки прав администратора"""
    
    async def __call__(self, obj: TelegramObject) -> bool:
        if isinstance(obj, (Message, CallbackQuery)):
            user_id = obj.from_user.id
            return user_id in ADMIN_IDS
        return False


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем ID пользователя
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        
        # Проверяем права администратора
        if user_id not in ADMIN_IDS:
            logger.warning(f"Попытка доступа к админским функциям от пользователя {user_id}")
            
            if isinstance(event, Message):
                await event.answer("❌ У вас нет прав администратора")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У вас нет прав администратора", show_alert=True)
            
            return
        
        # Логируем админские действия
        action = "unknown"
        if isinstance(event, Message) and event.text:
            action = event.text.split()[0]
        elif isinstance(event, CallbackQuery):
            action = event.data
        
        logger.info(f"Админ {user_id} выполняет действие: {action}")
        
        # Передаем управление дальше
        return await handler(event, data)


class UserTrackingMiddleware(BaseMiddleware):
    """Middleware для отслеживания активности пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем информацию о пользователе
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            
            # Логируем активность
            action = "message" if isinstance(event, Message) else "callback"
            logger.info(f"User {user.id} ({user.username}) performed {action}")
            
            # Добавляем информацию о пользователе в данные
            data['user_info'] = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_admin': user.id in ADMIN_IDS
            }
        
        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    """Middleware для защиты от спама"""
    
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self.users = {}  # {user_id: last_message_time}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        import time
        
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            current_time = time.time()
            
            # Проверяем время последнего сообщения
            if user_id in self.users:
                time_diff = current_time - self.users[user_id]
                if time_diff < self.rate_limit:
                    # Слишком частые сообщения
                    if isinstance(event, Message):
                        await event.answer("🚫 Не так быстро! Подождите немного.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Не так быстро!", show_alert=True)
                    return
            
            # Обновляем время последнего сообщения
            self.users[user_id] = current_time
        
        return await handler(event, data)


def setup_middlewares(dp):
    """Настройка middleware"""
    # Middleware для отслеживания пользователей (применяется ко всем событиям)
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
    # Anti-spam middleware (1 сообщение в секунду)
    dp.message.middleware(AntiSpamMiddleware(rate_limit=1))
    dp.callback_query.middleware(AntiSpamMiddleware(rate_limit=0.5))