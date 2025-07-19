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

# Импортируем конфигурацию с обработкой ошибок
try:
    from config.settings import TELEGRAM_BOT_TOKEN, LOG_LEVEL, LOG_DIR, YOOKASSA_SHOP_ID
except Exception as e:
    print(f"❌ Ошибка загрузки конфигурации: {e}")
    print("💡 Проверьте файл .env и убедитесь, что все переменные настроены")
    sys.exit(1)

from utils.logger import setup_logging
from database.database import init_database
from bot.handlers import register_all_handlers
from services.telegram_service import init_telegram_service


async def main():
    """Основная функция запуска бота"""
    
    # Настройка логирования
    setup_logging(level=LOG_LEVEL, log_dir=LOG_DIR)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск Telegram Payment Bot...")
    
    try:
        # Проверяем токен бота
        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден в .env")
            return
        
        # Инициализация базы данных
        logger.info("🗄️ Инициализация базы данных...")
        await init_database()
        logger.info("✅ База данных инициализирована")
        
        # Создание бота и диспетчера
        logger.info("🤖 Создание бота...")
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        
        # Инициализация telegram_service
        init_telegram_service(bot)
        logger.info("✅ Telegram сервис инициализирован")
        
        # Регистрация обработчиков
        logger.info("📋 Регистрация обработчиков...")
        register_all_handlers(dp)
        logger.info("✅ Обработчики зарегистрированы")
        
        # Запуск планировщика задач (только если не в режиме разработки)
        try:
            from tasks.scheduler import start_scheduler
            scheduler = start_scheduler()
            logger.info("✅ Планировщик задач запущен")
        except Exception as e:
            logger.warning(f"⚠️ Планировщик задач не запущен: {e}")
        
        # Запуск webhook сервера (только если настроен)
        webhook_task = None
        try:
            from webhook.server import start_webhook_server
            if YOOKASSA_SHOP_ID and YOOKASSA_SHOP_ID != 'test_shop_id':
                webhook_task = asyncio.create_task(start_webhook_server())
                logger.info("✅ Webhook сервер запущен")
            else:
                logger.info("⚠️ Webhook сервер не запущен (ЮKassa не настроена)")
        except Exception as e:
            logger.warning(f"⚠️ Webhook сервер не запущен: {e}")
        
        # Информация о боте
        try:
            bot_info = await bot.get_me()
            logger.info(f"✅ Бот запущен: @{bot_info.username} ({bot_info.first_name})")
            
            # Проверяем права в канале
            from config.settings import CHANNEL_ID
            try:
                chat = await bot.get_chat(CHANNEL_ID)
                logger.info(f"✅ Канал найден: {chat.title}")
                
                bot_member = await bot.get_chat_member(CHANNEL_ID, bot_info.id)
                if bot_member.status in ['administrator', 'creator']:
                    logger.info("✅ Бот имеет права администратора в канале")
                else:
                    logger.warning("⚠️ Бот не является администратором канала")
            except Exception as e:
                logger.error(f"❌ Ошибка проверки канала: {e}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о боте: {e}")
            return
        
        # Запуск поллинга
        logger.info("🔄 Начало поллинга...")
        logger.info("=" * 50)
        logger.info("🎉 БОТ УСПЕШНО ЗАПУЩЕН!")
        logger.info("📱 Напишите боту /start для тестирования")
        logger.info("=" * 50)
        
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    finally:
        # Завершение работы
        logger.info("🛑 Завершение работы бота...")
        if 'scheduler' in locals():
            try:
                scheduler.shutdown()
                logger.info("✅ Планировщик остановлен")
            except:
                pass
        if webhook_task and not webhook_task.done():
            webhook_task.cancel()
            logger.info("✅ Webhook сервер остановлен")


if __name__ == "__main__":
    try:
        # Проверяем версию Python
        if sys.version_info < (3, 9):
            print("❌ Требуется Python 3.9 или выше")
            sys.exit(1)
            
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)