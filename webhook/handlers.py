import logging
import json
import hmac
import hashlib
from datetime import datetime
from aiohttp.web import Request, Response, json_response

from config.settings import YOOKASSA_SECRET_KEY
from services.yookassa_service import yookassa_service
from services.subscription_service import subscription_service
from services.notification_service import notification_service
from database.database import db
from database.models import PaymentStatus
from utils.logger import payment_logger

logger = logging.getLogger("webhook")


def verify_yookassa_signature(body: bytes, signature: str) -> bool:
    """
    Проверка подписи webhook'а от YooKassa
    
    Args:
        body: Тело запроса
        signature: Подпись из заголовка
        
    Returns:
        True если подпись верна, False если нет
    """
    try:
        expected_signature = hmac.new(
            YOOKASSA_SECRET_KEY.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception as e:
        logger.error(f"Ошибка проверки подписи: {e}")
        return False


async def yookassa_webhook_handler(request: Request) -> Response:
    """
    Обработчик webhook'ов от YooKassa
    
    Args:
        request: HTTP запрос
        
    Returns:
        HTTP ответ
    """
    try:
        # Получаем тело запроса
        body = await request.read()
        
        # Получаем подпись из заголовков
        signature = request.headers.get('X-YooKassa-Signature', '')
        
        # В продакшене обязательно проверяем подпись!
        # if not verify_yookassa_signature(body, signature):
        #     logger.warning("Неверная подпись webhook'а YooKassa")
        #     return Response(status=400, text="Invalid signature")
        
        # Парсим JSON
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return Response(status=400, text="Invalid JSON")
        
        # Логируем получение webhook'а
        event_type = data.get('event', 'unknown')
        logger.info(f"Получен webhook YooKassa: {event_type}")
        
        # Обрабатываем уведомление
        await process_yookassa_notification(data)
        
        return Response(status=200, text="OK")
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook YooKassa: {e}")
        return Response(status=500, text="Internal error")


async def process_yookassa_notification(data: dict):
    """
    Обработка уведомления от YooKassa
    
    Args:
        data: Данные уведомления
    """
    try:
        event_type = data.get('event')
        payment_object = data.get('object', {})
        
        if not event_type or not payment_object:
            logger.warning("Некорректные данные webhook'а")
            return
        
        yookassa_payment_id = payment_object.get('id')
        status = payment_object.get('status')
        amount_data = payment_object.get('amount', {})
        amount = float(amount_data.get('value', 0))
        metadata = payment_object.get('metadata', {})
        
        # Получаем информацию о пользователе из метаданных
        user_id = metadata.get('user_id')
        bot_payment_id = metadata.get('bot_payment_id')
        
        if not user_id:
            logger.warning(f"Нет user_id в метаданных платежа {yookassa_payment_id}")
            return
        
        user_id = int(user_id)
        
        logger.info(f"Обработка события {event_type} для платежа {yookassa_payment_id}, пользователь {user_id}")
        
        # Получаем платеж из базы данных
        payment = None
        if bot_payment_id:
            payment = await db.get_payment(bot_payment_id)
        
        # Обрабатываем разные типы событий
        if event_type == 'payment.succeeded':
            await handle_payment_succeeded(user_id, yookassa_payment_id, amount, payment)
            
        elif event_type == 'payment.canceled':
            await handle_payment_canceled(user_id, yookassa_payment_id, payment)
            
        elif event_type == 'payment.waiting_for_capture':
            await handle_payment_waiting_capture(user_id, yookassa_payment_id, payment)
            
        elif event_type == 'refund.succeeded':
            await handle_refund_succeeded(user_id, yookassa_payment_id, amount)
            
        else:
            logger.info(f"Неизвестный тип события: {event_type}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки уведомления YooKassa: {e}")


async def handle_payment_succeeded(user_id: int, yookassa_payment_id: str, amount: float, payment=None):
    """
    Обработка успешного платежа
    
    Args:
        user_id: ID пользователя
        yookassa_payment_id: ID платежа в YooKassa
        amount: Сумма платежа
        payment: Объект платежа из БД (если есть)
    """
    try:
        # Обновляем платеж в базе данных
        if payment:
            payment.status = PaymentStatus.SUCCEEDED
            payment.completed_at = datetime.now()
            await db.save_payment(payment)
            
            # Активируем подписку
            success = await subscription_service.activate_subscription(user_id, payment)
            
            if success:
                payment_logger.payment_succeeded(user_id, payment.payment_id, amount)
                logger.info(f"Подписка активирована для пользователя {user_id}")
            else:
                logger.error(f"Ошибка активации подписки для пользователя {user_id}")
                # Отправляем уведомление об ошибке
                await notification_service.send_payment_failed(
                    user_id, "Ошибка активации подписки. Обратитесь в поддержку."
                )
        else:
            logger.warning(f"Платеж не найден в БД для YooKassa ID {yookassa_payment_id}")
            
            # Можем попробовать найти пользователя и активировать подписку вручную
            # Но это рискованно без проверки суммы и других параметров
            
    except Exception as e:
        logger.error(f"Ошибка обработки успешного платежа: {e}")


async def handle_payment_canceled(user_id: int, yookassa_payment_id: str, payment=None):
    """
    Обработка отмененного платежа
    
    Args:
        user_id: ID пользователя
        yookassa_payment_id: ID платежа в YooKassa
        payment: Объект платежа из БД (если есть)
    """
    try:
        # Обновляем платеж в базе данных
        if payment:
            payment.status = PaymentStatus.CANCELED
            await db.save_payment(payment)
            
            payment_logger.payment_failed(user_id, payment.payment_id, "canceled")
        
        # Отправляем уведомление пользователю
        await notification_service.send_payment_failed(user_id, "Платеж отменен")
        
        logger.info(f"Платеж {yookassa_payment_id} отменен для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки отмененного платежа: {e}")


async def handle_payment_waiting_capture(user_id: int, yookassa_payment_id: str, payment=None):
    """
    Обработка платежа, ожидающего подтверждения
    
    Args:
        user_id: ID пользователя
        yookassa_payment_id: ID платежа в YooKassa
        payment: Объект платежа из БД (если есть)
    """
    try:
        logger.info(f"Платеж {yookassa_payment_id} ожидает подтверждения")
        
        # Можем автоматически подтвердить платеж
        success = await yookassa_service.capture_payment(yookassa_payment_id)
        
        if success:
            logger.info(f"Платеж {yookassa_payment_id} автоматически подтвержден")
        else:
            logger.error(f"Ошибка подтверждения платежа {yookassa_payment_id}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки платежа waiting_for_capture: {e}")


async def handle_refund_succeeded(user_id: int, yookassa_payment_id: str, amount: float):
    """
    Обработка успешного возврата
    
    Args:
        user_id: ID пользователя
        yookassa_payment_id: ID платежа в YooKassa
        amount: Сумма возврата
    """
    try:
        logger.info(f"Возврат {amount} руб. для пользователя {user_id}")
        
        # Отправляем уведомление пользователю
        await notification_service.send_message(
            user_id,
            f"💰 <b>Возврат средств</b>\n\n"
            f"Сумма: {amount} руб\n"
            f"Средства поступят на ваш счет в течение 3-7 рабочих дней."
        )
        
        # Можем отменить подписку если нужно
        await subscription_service.cancel_subscription(user_id, "refund")
        
    except Exception as e:
        logger.error(f"Ошибка обработки возврата: {e}")


async def health_check_handler(request: Request) -> Response:
    """
    Обработчик проверки здоровья сервиса
    
    Args:
        request: HTTP запрос
        
    Returns:
        JSON ответ со статусом сервиса
    """
    try:
        return json_response({
            "status": "healthy",
            "service": "Payment Bot Webhook Server",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        })
        
    except Exception as e:
        logger.error(f"Ошибка health check: {e}")
        return json_response(
            {"status": "error", "message": str(e)},
            status=500
        )