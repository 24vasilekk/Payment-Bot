import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config.settings import ADMIN_IDS, SUBSCRIPTION_PRICE
from services.subscription_service import subscription_service
from services.telegram_service import telegram_service
from bot.keyboards.inline import get_admin_keyboard, get_confirmation_keyboard, get_user_management_keyboard
from bot.states.payment_states import AdminStates
from bot.middleware.auth import AdminFilter
from database.database import db

logger = logging.getLogger(__name__)
router = Router()

# Применяем фильтр админов ко всем хендлерам в этом роутере
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главная админ панель"""
    try:
        await message.answer(
            "🔧 <b>Панель администратора</b>\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в админ панели: {e}")
        await message.answer("❌ Ошибка открытия админ панели")


@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Статистика пользователей и платежей"""
    try:
        # Получаем статистику
        user_stats = await subscription_service.get_users_count_by_status()
        revenue_stats = await subscription_service.get_revenue_stats(days=30)
        
        # Получаем информацию о канале
        channel_info = await telegram_service.get_channel_info()
        member_count = channel_info.get("member_count", "Неизвестно") if channel_info else "Неизвестно"
        
        message = f"""
📊 <b>Статистика системы</b>

👥 <b>Пользователи:</b>
• Активных подписок: {user_stats.get('active', 0)}
• Истекших: {user_stats.get('expired', 0)}
• На пробном периоде: {user_stats.get('trial', 0)}
• Заблокированных: {user_stats.get('suspended', 0)}
• Всего зарегистрировано: {user_stats.get('total', 0)}

💰 <b>Доходы (30 дней):</b>
• Общая сумма: {revenue_stats.get('total_revenue', 0)} руб
• Успешных платежей: {revenue_stats.get('successful_payments', 0)}
• Неудачных платежей: {revenue_stats.get('failed_payments', 0)}

📢 <b>Канал:</b>
• Участников: {member_count}
• Цена подписки: {SUBSCRIPTION_PRICE} руб/мес
        """.strip()
        
        await callback.message.edit_text(
            message,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("📊 Статистика обновлена")
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)


@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery):
    """Управление пользователями"""
    try:
        message = """
👥 <b>Управление пользователями</b>

Введите ID пользователя для управления:
        """.strip()
        
        await callback.message.edit_text(
            message,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в управлении пользователями: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Рассылка сообщений"""
    try:
        await callback.message.edit_text(
            "📢 <b>Рассылка сообщений</b>\n\n"
            "Отправьте сообщение, которое нужно разослать всем пользователям:",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(AdminStates.waiting_broadcast_message)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в рассылке: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminStates.waiting_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    try:
        broadcast_text = message.text or message.caption or "Сообщение без текста"
        
        # Получаем всех активных пользователей (упрощенная версия)
        # В реальном проекте нужен отдельный метод для получения всех пользователей
        user_ids = [123456789]  # Заглушка
        
        # Показываем подтверждение
        confirmation_text = f"""
📢 <b>Подтверждение рассылки</b>

<b>Сообщение:</b>
{broadcast_text[:200]}{'...' if len(broadcast_text) > 200 else ''}

<b>Количество получателей:</b> {len(user_ids)}

Отправить рассылку?
        """.strip()
        
        await state.update_data(
            broadcast_text=broadcast_text,
            user_ids=user_ids
        )
        
        await message.answer(
            confirmation_text,
            reply_markup=get_confirmation_keyboard("broadcast"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения для рассылки: {e}")
        await message.answer("❌ Ошибка обработки сообщения")
        await state.clear()


@router.callback_query(F.data.startswith("confirm:broadcast"))
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и выполнение рассылки"""
    try:
        data = await state.get_data()
        broadcast_text = data.get('broadcast_text')
        user_ids = data.get('user_ids', [])
        
        if not broadcast_text or not user_ids:
            await callback.answer("❌ Данные для рассылки не найдены", show_alert=True)
            await state.clear()
            return
        
        await callback.message.edit_text("📤 Начинаем рассылку...")
        
        # Выполняем рассылку
        results = await telegram_service.broadcast_message(user_ids, broadcast_text)
        
        # Показываем результаты
        result_text = f"""
✅ <b>Рассылка завершена</b>

📊 <b>Результаты:</b>
• Отправлено: {results['sent']}
• Заблокировано: {results['blocked']}
• Ошибки: {results['failed']}
• Всего: {results['total']}
        """.strip()
        
        await callback.message.edit_text(
            result_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        
        await state.clear()
        logger.info(f"Рассылка выполнена админом {callback.from_user.id}: {results}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения рассылки: {e}")
        await callback.answer("❌ Ошибка выполнения рассылки", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "admin_payments")
async def admin_payments_callback(callback: CallbackQuery):
    """Управление платежами"""
    try:
        message = """
💰 <b>Управление платежами</b>

Доступные действия:
• Просмотр последних платежей
• Поиск платежа по ID
• Создание возврата
• Статистика по платежам

Функционал в разработке...
        """.strip()
        
        await callback.message.edit_text(
            message,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в управлении платежами: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: CallbackQuery):
    """Настройки системы"""
    try:
        from config.settings import SUBSCRIPTION_PRICE, SUBSCRIPTION_DURATION_DAYS, WEBHOOK_HOST
        
        message = f"""
⚙️ <b>Настройки системы</b>

<b>Подписка:</b>
• Цена: {SUBSCRIPTION_PRICE} руб
• Длительность: {SUBSCRIPTION_DURATION_DAYS} дней

<b>Webhook:</b>
• Хост: {WEBHOOK_HOST}

<b>Канал:</b>
• ID: {telegram_service.channel_id if telegram_service else 'Не настроен'}

Для изменения настроек отредактируйте .env файл и перезапустите бота.
        """.strip()
        
        await callback.message.edit_text(
            message,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в настройках: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_logs")
async def admin_logs_callback(callback: CallbackQuery):
    """Просмотр логов"""
    try:
        import os
        from pathlib import Path
        from config.settings import LOG_DIR
        
        log_files = []
        if LOG_DIR.exists():
            for log_file in LOG_DIR.glob("*.log"):
                size = log_file.stat().st_size
                size_mb = size / (1024 * 1024)
                log_files.append(f"• {log_file.name}: {size_mb:.1f} MB")
        
        message = f"""
📝 <b>Логи системы</b>

<b>Файлы логов:</b>
{chr(10).join(log_files) if log_files else '• Логи не найдены'}

<b>Директория:</b> {LOG_DIR}

Для просмотра логов используйте команды сервера или файловый менеджер.
        """.strip()
        
        await callback.message.edit_text(
            message,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка просмотра логов: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(Command("kick"))
async def kick_user_command(message: Message):
    """Команда исключения пользователя"""
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("❌ Использование: /kick <user_id>")
            return
        
        try:
            user_id = int(args[1])
        except ValueError:
            await message.answer("❌ Некорректный ID пользователя")
            return
        
        # Отменяем подписку
        success = await subscription_service.cancel_subscription(user_id, "admin_kick")
        
        if success:
            await message.answer(f"✅ Пользователь {user_id} исключен из канала")
        else:
            await message.answer(f"❌ Ошибка исключения пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка команды /kick: {e}")
        await message.answer("❌ Ошибка выполнения команды")


@router.message(Command("extend"))
async def extend_subscription_command(message: Message):
    """Команда продления подписки"""
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer("❌ Использование: /extend <user_id> <days>")
            return
        
        try:
            user_id = int(args[1])
            days = int(args[2])
        except ValueError:
            await message.answer("❌ Некорректные параметры")
            return
        
        if days <= 0 or days > 365:
            await message.answer("❌ Количество дней должно быть от 1 до 365")
            return
        
        # Продлеваем подписку
        success = await subscription_service.extend_subscription(user_id, days, "admin_extension")
        
        if success:
            await message.answer(f"✅ Подписка пользователя {user_id} продлена на {days} дней")
        else:
            await message.answer(f"❌ Ошибка продления подписки для {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка команды /extend: {e}")
        await message.answer("❌ Ошибка выполнения команды")


def register_handlers(dp):
    """Регистрация админских обработчиков"""
    dp.include_router(router)