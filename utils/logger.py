import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(level: str = "INFO", log_dir: Path = None):
    """
    Настройка системы логирования
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Директория для файлов логов
    """
    
    # Создание директории логов
    if log_dir:
        log_dir.mkdir(exist_ok=True)
    
    # Настройка уровня логирования
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Форматы логов
    console_format = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_format = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | %(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очистка существующих обработчиков
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    if log_dir:
        # Основной файл лога
        main_log_file = log_dir / 'bot.log'
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(log_level)
        main_handler.setFormatter(file_format)
        root_logger.addHandler(main_handler)
        
        # Файл для ошибок
        error_log_file = log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        root_logger.addHandler(error_handler)
        
        # Отдельный лог для webhook'ов
        webhook_logger = logging.getLogger('webhook')
        webhook_log_file = log_dir / 'webhook.log'
        webhook_handler = logging.handlers.RotatingFileHandler(
            webhook_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        webhook_handler.setLevel(logging.INFO)
        webhook_handler.setFormatter(file_format)
        webhook_logger.addHandler(webhook_handler)
        webhook_logger.propagate = False  # Не дублировать в основном логе
    
    # Настройка сторонних библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Логгер для платежей (важные события)
    payment_logger = logging.getLogger('payments')
    if log_dir:
        payment_log_file = log_dir / 'payments.log'
        payment_handler = logging.handlers.RotatingFileHandler(
            payment_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10,  # Храним больше истории для платежей
            encoding='utf-8'
        )
        payment_handler.setLevel(logging.INFO)
        payment_handler.setFormatter(file_format)
        payment_logger.addHandler(payment_handler)
    
    logging.info(f"Логирование настроено. Уровень: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с заданным именем
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


class PaymentLogger:
    """Специальный логгер для отслеживания платежей"""
    
    def __init__(self):
        self.logger = logging.getLogger('payments')
    
    def payment_created(self, user_id: int, payment_id: str, amount: float):
        """Логирование создания платежа"""
        self.logger.info(f"PAYMENT_CREATED | User: {user_id} | Payment: {payment_id} | Amount: {amount}")
    
    def payment_succeeded(self, user_id: int, payment_id: str, amount: float):
        """Логирование успешного платежа"""
        self.logger.info(f"PAYMENT_SUCCEEDED | User: {user_id} | Payment: {payment_id} | Amount: {amount}")
    
    def payment_failed(self, user_id: int, payment_id: str, reason: str = ""):
        """Логирование неудачного платежа"""
        self.logger.warning(f"PAYMENT_FAILED | User: {user_id} | Payment: {payment_id} | Reason: {reason}")
    
    def subscription_extended(self, user_id: int, end_date: datetime):
        """Логирование продления подписки"""
        self.logger.info(f"SUBSCRIPTION_EXTENDED | User: {user_id} | End: {end_date}")
    
    def subscription_expired(self, user_id: int):
        """Логирование истечения подписки"""
        self.logger.warning(f"SUBSCRIPTION_EXPIRED | User: {user_id}")
    
    def user_kicked(self, user_id: int, reason: str = "subscription_expired"):
        """Логирование исключения пользователя"""
        self.logger.warning(f"USER_KICKED | User: {user_id} | Reason: {reason}")


# Глобальный экземпляр для платежей
payment_logger = PaymentLogger()