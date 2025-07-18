import logging
import asyncio
import functools
from datetime import datetime, timedelta
from typing import Callable, Dict, Any
from aiogram.types import Message, CallbackQuery

from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)


def admin_required(func: Callable) -> Callable:
    """
    Декоратор для проверки прав администратора
    
    Args:
        func: Функция-обработчик
        
    Returns:
        Обернутая функция
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Ищем объект с from_user среди аргументов
        user_id = None
        for arg in args:
            if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                user_id = arg.from_user.id
                break
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"Попытка доступа к админской функции от пользователя {user_id}")
            
            # Находим объект для ответа
            for arg in args:
                if isinstance(arg, Message):
                    await arg.answer("❌ У вас нет прав администратора")
                    return
                elif isinstance(arg, CallbackQuery):
                    await arg.answer("❌ У вас нет прав администратора", show_alert=True)
                    return
            
            return
        
        return await func(*args, **kwargs)
    
    return wrapper


def rate_limit(limit: int = 1, window: int = 60):
    """
    Декоратор для ограничения частоты вызовов
    
    Args:
        limit: Максимальное количество вызовов
        window: Временное окно в секундах
        
    Returns:
        Декоратор
    """
    calls: Dict[int, list] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Получаем user_id
            user_id = None
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
            
            if user_id is None:
                return await func(*args, **kwargs)
            
            now = datetime.now()
            
            # Инициализируем список вызовов для пользователя
            if user_id not in calls:
                calls[user_id] = []
            
            user_calls = calls[user_id]
            
            # Удаляем старые вызовы
            cutoff = now - timedelta(seconds=window)
            user_calls[:] = [call_time for call_time in user_calls if call_time > cutoff]
            
            # Проверяем лимит
            if len(user_calls) >= limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                
                # Отправляем сообщение о превышении лимита
                for arg in args:
                    if isinstance(arg, Message):
                        await arg.answer("🚫 Слишком много запросов. Попробуйте позже.")
                        return
                    elif isinstance(arg, CallbackQuery):
                        await arg.answer("🚫 Слишком много запросов", show_alert=True)
                        return
                
                return
            
            # Добавляем текущий вызов
            user_calls.append(now)
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def log_calls(level: int = logging.INFO):
    """
    Декоратор для логирования вызовов функций
    
    Args:
        level: Уровень логирования
        
    Returns:
        Декоратор
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Получаем информацию о пользователе
            user_info = "unknown"
            for arg in args:
                if hasattr(arg, 'from_user'):
                    user = arg.from_user
                    user_info = f"{user.id} (@{user.username or 'no_username'})"
                    break
            
            logger.log(level, f"Calling {func.__name__} for user {user_info}")
            
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"Successfully completed {func.__name__} for user {user_info}")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__} for user {user_info}: {e}")
                raise
        
        return wrapper
    
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Декоратор для повторных попыток выполнения функции
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками
        backoff: Множитель для увеличения задержки
        
    Returns:
        Декоратор
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:  # Не последняя попытка
                        logger.warning(
                            f"Attempt {attempt + 1} of {func.__name__} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts of {func.__name__} failed. "
                            f"Last error: {e}"
                        )
            
            # Если все попытки неудачны, выбрасываем последнее исключение
            raise last_exception
        
        return wrapper
    
    return decorator


def error_handler(send_error_message: bool = True):
    """
    Декоратор для обработки ошибок в хендлерах
    
    Args:
        send_error_message: Отправлять ли сообщение об ошибке пользователю
        
    Returns:
        Декоратор
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                
                if send_error_message:
                    # Пытаемся отправить сообщение об ошибке
                    for arg in args:
                        if isinstance(arg, Message):
                            try:
                                await arg.answer("❌ Произошла ошибка. Попробуйте позже.")
                            except:
                                pass
                            break
                        elif isinstance(arg, CallbackQuery):
                            try:
                                await arg.answer("❌ Произошла ошибка", show_alert=True)
                            except:
                                pass
                            break
                
                # Не перевыбрасываем исключение, чтобы не ломать бота
                return None
        
        return wrapper
    
    return decorator


def subscription_required(func: Callable) -> Callable:
    """
    Декоратор для проверки активной подписки
    
    Args:
        func: Функция-обработчик
        
    Returns:
        Обернутая функция
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from services.subscription_service import subscription_service
        from bot.keyboards.inline import get_subscription_keyboard
        
        # Получаем user_id
        user_id = None
        message_obj = None
        
        for arg in args:
            if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                user_id = arg.from_user.id
                message_obj = arg
                break
        
        if user_id is None:
            return await func(*args, **kwargs)
        
        # Проверяем статус подписки
        status = await subscription_service.get_subscription_status(user_id)
        
        if not status or not status['is_active']:
            # Подписка неактивна
            if isinstance(message_obj, Message):
                await message_obj.answer(
                    "❌ Для использования этой функции требуется активная подписка.\n\n"
                    "Используйте /pay для оформления подписки.",
                    reply_markup=get_subscription_keyboard()
                )
            elif isinstance(message_obj, CallbackQuery):
                await message_obj.answer(
                    "❌ Требуется активная подписка",
                    show_alert=True
                )
            
            return
        
        return await func(*args, **kwargs)
    
    return wrapper


def measure_time(func: Callable) -> Callable:
    """
    Декоратор для измерения времени выполнения функции
    
    Args:
        func: Функция для измерения
        
    Returns:
        Обернутая функция
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


def cache_result(ttl: int = 300):
    """
    Декоратор для кэширования результатов функций
    
    Args:
        ttl: Время жизни кэша в секундах
        
    Returns:
        Декоратор
    """
    cache: Dict[str, tuple] = {}  # {key: (result, expiry_time)}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кэша
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            now = datetime.now()
            
            # Проверяем кэш
            if cache_key in cache:
                result, expiry_time = cache[cache_key]
                if now < expiry_time:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                else:
                    # Удаляем устаревшую запись
                    del cache[cache_key]
            
            # Выполняем функцию и кэшируем результат
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, now + timedelta(seconds=ttl))
            
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
        
        return wrapper
    
    return decorator