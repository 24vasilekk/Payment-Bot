#!/usr/bin/env python3
"""
Telegram Payment Bot - Основной файл запуска
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import TELEGRAM_BOT_TOKEN, LOG_LEVEL, LOG_DIR
from utils.logger import setup_logging
from database.database import init_database
from bot.handlers import register_all_handlers
from tasks.scheduler import start_scheduler
from webhook.server import start_webhook_server


async def main():
    """Основная функция запуска бота"""
    
    # Настройка логирования
    setup_logging(level=LOG_LEVEL, log_dir=LOG_DIR)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск Telegram Payment Bot...")
    
    try:
        # Инициализация базы данных
        await init_database()
        logger.info("✅ База данных инициализирована")
        
        # Создание бота и диспетчера
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        
        # Регистрация обработчиков
        register_all_handlers(dp)
        logger.info("✅ Обработчики зарегистрированы")
        
        # Запуск планировщика задач
        scheduler = start_scheduler()
        logger.info("✅ Планировщик задач запущен")
        
        # Запуск webhook сервера в отдельной задаче
        webhook_task = asyncio.create_task(start_webhook_server())
        logger.info("✅ Webhook сервер запущен")
        
        # Информация о боте
        bot_info = await bot.get_me()
        logger.info(f"✅ Бот запущен: @{bot_info.username}")
        
        # Запуск поллинга
        logger.info("🔄 Начало поллинга...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        sys.exit(1)
    
    finally:
        # Завершение работы
        logger.info("🛑 Завершение работы бота...")
        if 'scheduler' in locals():
            scheduler.shutdown()
        if 'webhook_task' in locals():
            webhook_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)