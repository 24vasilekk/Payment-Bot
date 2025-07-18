import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config.settings import CHECK_SUBSCRIPTIONS_INTERVAL_MINUTES, ADMIN_IDS
from tasks.subscription_checker import check_expired_subscriptions, send_expiration_reminders
from services.notification_service import notification_service

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Планировщик фоновых задач"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Запуск планировщика"""
        try:
            # Добавляем задачи
            self._add_tasks()
            
            # Запускаем планировщик
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Планировщик задач запущен")
            
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")
            raise
    
    def stop(self):
        """Остановка планировщика"""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("Планировщик задач остановлен")
                
        except Exception as e:
            logger.error(f"Ошибка остановки планировщика: {e}")
    
    def _add_tasks(self):
        """Добавление задач в планировщик"""
        
        # 1. Проверка истекших подписок каждый час
        self.scheduler.add_job(
            check_expired_subscriptions,
            trigger=IntervalTrigger(minutes=CHECK_SUBSCRIPTIONS_INTERVAL_MINUTES),
            id='check_expired_subscriptions',
            name='Проверка истекших подписок',
            max_instances=1,
            misfire_grace_time=300  # 5 минут допустимой задержки
        )
        
        # 2. Отправка напоминаний о скором истечении подписок (2 раза в день)
        self.scheduler.add_job(
            send_expiration_reminders,
            trigger=CronTrigger(hour='9,21', minute=0),  # 9:00 и 21:00
            id='send_expiration_reminders',
            name='Отправка напоминаний об истечении',
            max_instances=1
        )
        
        # 3. Ежедневная статистика для админов (в 9:00)
        self.scheduler.add_job(
            self._send_daily_stats,
            trigger=CronTrigger(hour=9, minute=0),
            id='send_daily_stats',
            name='Ежедневная статистика',
            max_instances=1
        )
        
        # 4. Еженедельная статистика (в понедельник в 10:00)
        self.scheduler.add_job(
            self._send_weekly_stats,
            trigger=CronTrigger(day_of_week='mon', hour=10, minute=0),
            id='send_weekly_stats',
            name='Еженедельная статистика',
            max_instances=1
        )
        
        # 5. Очистка старых логов (раз в неделю, в воскресенье в 3:00)
        self.scheduler.add_job(
            self._cleanup_old_logs,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='cleanup_old_logs',
            name='Очистка старых логов',
            max_instances=1
        )
        
        # 6. Бэкап базы данных (каждый день в 2:00)
        self.scheduler.add_job(
            self._backup_database,
            trigger=CronTrigger(hour=2, minute=0),
            id='backup_database',
            name='Бэкап базы данных',
            max_instances=1
        )
        
        logger.info("Задачи добавлены в планировщик")
    
    async def _send_daily_stats(self):
        """Отправка ежедневной статистики админам"""
        try:
            from services.subscription_service import subscription_service
            
            # Получаем статистику
            user_stats = await subscription_service.get_users_count_by_status()
            revenue_stats = await subscription_service.get_revenue_stats(days=1)
            
            message = f"""
📊 <b>Ежедневная статистика</b>
📅 {datetime.now().strftime('%d.%m.%Y')}

👥 <b>Пользователи:</b>
• Активных: {user_stats.get('active', 0)}
• Истекших: {user_stats.get('expired', 0)}
• Пробных: {user_stats.get('trial', 0)}
• Всего: {user_stats.get('total', 0)}

💰 <b>Доходы за сутки:</b>
• Сумма: {revenue_stats.get('total_revenue', 0)} руб
• Успешных платежей: {revenue_stats.get('successful_payments', 0)}
• Неудачных: {revenue_stats.get('failed_payments', 0)}

⏰ {datetime.now().strftime('%H:%M')}
            """.strip()
            
            # Отправляем всем админам
            for admin_id in ADMIN_IDS:
                await notification_service.send_admin_notification(admin_id, message)
            
            logger.info("Ежедневная статистика отправлена админам")
            
        except Exception as e:
            logger.error(f"Ошибка отправки ежедневной статистики: {e}")
    
    async def _send_weekly_stats(self):
        """Отправка еженедельной статистики админам"""
        try:
            from services.subscription_service import subscription_service
            
            # Получаем статистику за неделю
            revenue_stats = await subscription_service.get_revenue_stats(days=7)
            
            message = f"""
📈 <b>Еженедельная статистика</b>
📅 {datetime.now().strftime('%d.%m.%Y')}

💰 <b>Доходы за неделю:</b>
• Общая сумма: {revenue_stats.get('total_revenue', 0)} руб
• Успешных платежей: {revenue_stats.get('successful_payments', 0)}
• Неудачных: {revenue_stats.get('failed_payments', 0)}
• Конверсия: {revenue_stats.get('conversion_rate', 0):.1f}%

📊 <b>Тренды:</b>
• Средний чек: {revenue_stats.get('average_payment', 0):.0f} руб
• Доходность: {revenue_stats.get('growth_rate', 0):+.1f}%

⏰ {datetime.now().strftime('%H:%M')}
            """.strip()
            
            # Отправляем всем админам
            for admin_id in ADMIN_IDS:
                await notification_service.send_admin_notification(admin_id, message)
            
            logger.info("Еженедельная статистика отправлена админам")
            
        except Exception as e:
            logger.error(f"Ошибка отправки еженедельной статистики: {e}")
    
    async def _cleanup_old_logs(self):
        """Очистка старых файлов логов"""
        try:
            import os
            from pathlib import Path
            from config.settings import LOG_DIR
            
            # Удаляем логи старше 30 дней
            cutoff_date = datetime.now() - timedelta(days=30)
            deleted_count = 0
            
            for log_file in Path(LOG_DIR).glob("*.log.*"):
                try:
                    # Проверяем дату модификации файла
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        log_file.unlink()
                        deleted_count += 1
                        
                except Exception as e:
                    logger.warning(f"Ошибка удаления лога {log_file}: {e}")
            
            logger.info(f"Очистка логов завершена. Удалено файлов: {deleted_count}")
            
            # Уведомляем админов
            for admin_id in ADMIN_IDS:
                await notification_service.send_admin_notification(
                    admin_id,
                    f"🧹 Очистка логов завершена\nУдалено файлов: {deleted_count}"
                )
            
        except Exception as e:
            logger.error(f"Ошибка очистки логов: {e}")
    
    async def _backup_database(self):
        """Создание бэкапа базы данных"""
        try:
            import shutil
            from pathlib import Path
            from config.settings import DATABASE_PATH
            
            # Создаем директорию для бэкапов
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            # Имя файла бэкапа с датой
            backup_name = f"users_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = backup_dir / backup_name
            
            # Копируем файл базы данных
            shutil.copy2(DATABASE_PATH, backup_path)
            
            # Удаляем старые бэкапы (оставляем последние 7)
            backup_files = sorted(backup_dir.glob("users_backup_*.db"))
            if len(backup_files) > 7:
                for old_backup in backup_files[:-7]:
                    old_backup.unlink()
            
            logger.info(f"Бэкап базы данных создан: {backup_path}")
            
            # Уведомляем админов
            for admin_id in ADMIN_IDS:
                await notification_service.send_admin_notification(
                    admin_id,
                    f"💾 Бэкап базы данных создан\nФайл: {backup_name}"
                )
            
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            
            # Уведомляем админов об ошибке
            for admin_id in ADMIN_IDS:
                await notification_service.send_admin_notification(
                    admin_id,
                    f"❌ Ошибка создания бэкапа базы данных: {str(e)}"
                )
    
    def get_job_status(self) -> dict:
        """Получить статус всех задач"""
        try:
            jobs_info = {}
            
            for job in self.scheduler.get_jobs():
                jobs_info[job.id] = {
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
            
            return {
                "scheduler_running": self.is_running,
                "jobs_count": len(jobs_info),
                "jobs": jobs_info
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса задач: {e}")
            return {"error": str(e)}


# Глобальный экземпляр планировщика
task_scheduler = TaskScheduler()


def start_scheduler() -> TaskScheduler:
    """
    Запуск планировщика задач
    
    Returns:
        Экземпляр планировщика
    """
    try:
        task_scheduler.start()
        return task_scheduler
        
    except Exception as e:
        logger.error(f"Ошибка запуска планировщика: {e}")
        raise


def stop_scheduler():
    """Остановка планировщика задач"""
    try:
        task_scheduler.stop()
        
    except Exception as e:
        logger.error(f"Ошибка остановки планировщика: {e}")