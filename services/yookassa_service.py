import aiohttp
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from config.settings import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, YOOKASSA_BASE_URL
from database.models import Payment, PaymentStatus
from utils.logger import payment_logger

logger = logging.getLogger(__name__)


class YooKassaService:
    """Сервис для работы с YooKassa API"""
    
    def __init__(self):
        self.shop_id = YOOKASSA_SHOP_ID
        self.secret_key = YOOKASSA_SECRET_KEY
        self.base_url = YOOKASSA_BASE_URL
        self.test_mode = not self.shop_id or self.shop_id == 'test_shop_id'
        
        if self.test_mode:
            logger.warning("ЮKassa работает в тестовом режиме")
        
    def _get_auth(self) -> aiohttp.BasicAuth:
        """Получить авторизацию для запросов"""
        return aiohttp.BasicAuth(self.shop_id, self.secret_key)
    
    async def create_payment(
        self, 
        amount: float, 
        description: str, 
        user_id: int,
        return_url: str = None
    ) -> Optional[Payment]:
        """
        Создать платеж в YooKassa
        
        Args:
            amount: Сумма платежа
            description: Описание платежа  
            user_id: ID пользователя
            return_url: URL для возврата после оплаты
            
        Returns:
            Объект Payment или None при ошибке
        """
        try:
            payment_id = str(uuid.uuid4())
            
            # В тестовом режиме возвращаем мок-платеж
            if self.test_mode:
                logger.info(f"Создание тестового платежа для пользователя {user_id}")
                
                payment = Payment(
                    payment_id=payment_id,
                    yookassa_payment_id=f"test_{payment_id}",
                    user_id=user_id,
                    amount=amount,
                    description=description,
                    status=PaymentStatus.PENDING,
                    confirmation_url=f"https://test-payment-url.com/pay/{payment_id}",
                    metadata={"user_id": str(user_id), "bot_payment_id": payment_id},
                    created_at=datetime.now()
                )
                
                payment_logger.payment_created(user_id, payment_id, amount)
                logger.info(f"Создан тестовый платеж {payment_id} для пользователя {user_id}")
                
                return payment
            
            # Реальный режим ЮKassa
            data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url or "https://t.me/"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "bot_payment_id": payment_id
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Idempotence-Key": payment_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/payments",
                    json=data,
                    headers=headers,
                    auth=self._get_auth()
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        payment = Payment(
                            payment_id=payment_id,
                            yookassa_payment_id=result["id"],
                            user_id=user_id,
                            amount=amount,
                            description=description,
                            status=PaymentStatus.PENDING,
                            confirmation_url=result["confirmation"]["confirmation_url"],
                            metadata=result.get("metadata", {}),
                            created_at=datetime.now()
                        )
                        
                        payment_logger.payment_created(user_id, payment_id, amount)
                        logger.info(f"Создан платеж {payment_id} для пользователя {user_id}")
                        
                        return payment
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка создания платежа: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение при создании платежа: {e}")
            return None
    
    async def get_payment_info(self, yookassa_payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о платеже
        
        Args:
            yookassa_payment_id: ID платежа в YooKassa
            
        Returns:
            Словарь с информацией о платеже или None
        """
        try:
            # В тестовом режиме возвращаем мок-данные
            if self.test_mode:
                if yookassa_payment_id.startswith("test_"):
                    logger.info(f"Получение информации о тестовом платеже {yookassa_payment_id}")
                    return {
                        "id": yookassa_payment_id,
                        "status": "succeeded",  # Всегда успешно в тесте
                        "amount": {"value": "500.00", "currency": "RUB"},
                        "metadata": {"test": "true"}
                    }
                return None
            
            # Реальный запрос к ЮKassa
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/payments/{yookassa_payment_id}",
                    auth=self._get_auth()
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Ошибка получения платежа: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение при получении платежа: {e}")
            return None
    
    async def capture_payment(self, yookassa_payment_id: str, amount: float = None) -> bool:
        """
        Подтвердить платеж (capture)
        
        Args:
            yookassa_payment_id: ID платежа в YooKassa
            amount: Сумма для подтверждения (опционально)
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # В тестовом режиме всегда успешно
            if self.test_mode:
                logger.info(f"Тестовое подтверждение платежа {yookassa_payment_id}")
                return True
            
            data = {}
            if amount:
                data["amount"] = {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/payments/{yookassa_payment_id}/capture",
                    json=data,
                    auth=self._get_auth()
                ) as response:
                    
                    if response.status == 200:
                        logger.info(f"Платеж {yookassa_payment_id} подтвержден")
                        return True
                    else:
                        logger.error(f"Ошибка подтверждения платежа: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Исключение при подтверждении платежа: {e}")
            return False
    
    async def cancel_payment(self, yookassa_payment_id: str) -> bool:
        """
        Отменить платеж
        
        Args:
            yookassa_payment_id: ID платежа в YooKassa
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # В тестовом режиме всегда успешно
            if self.test_mode:
                logger.info(f"Тестовая отмена платежа {yookassa_payment_id}")
                return True
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/payments/{yookassa_payment_id}/cancel",
                    auth=self._get_auth()
                ) as response:
                    
                    if response.status == 200:
                        logger.info(f"Платеж {yookassa_payment_id} отменен")
                        return True
                    else:
                        logger.error(f"Ошибка отмены платежа: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Исключение при отмене платежа: {e}")
            return False
    
    async def create_refund(
        self, 
        yookassa_payment_id: str, 
        amount: float,
        description: str = "Возврат средств"
    ) -> Optional[str]:
        """
        Создать возврат
        
        Args:
            yookassa_payment_id: ID платежа для возврата
            amount: Сумма возврата
            description: Описание возврата
            
        Returns:
            ID возврата или None при ошибке
        """
        try:
            # В тестовом режиме возвращаем тестовый ID
            if self.test_mode:
                refund_id = f"test_refund_{uuid.uuid4()}"
                logger.info(f"Создан тестовый возврат {refund_id} для платежа {yookassa_payment_id}")
                return refund_id
            
            data = {
                "payment_id": yookassa_payment_id,
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "description": description
            }
            
            headers = {
                "Content-Type": "application/json",
                "Idempotence-Key": str(uuid.uuid4())
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/refunds",
                    json=data,
                    headers=headers,
                    auth=self._get_auth()
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        refund_id = result["id"]
                        logger.info(f"Создан возврат {refund_id} для платежа {yookassa_payment_id}")
                        return refund_id
                    else:
                        logger.error(f"Ошибка создания возврата: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Исключение при создании возврата: {e}")
            return None
    
    def parse_webhook_notification(self, notification_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обработать уведомление webhook
        
        Args:
            notification_data: Данные уведомления
            
        Returns:
            Обработанные данные или None
        """
        try:
            event_type = notification_data.get("event")
            payment_object = notification_data.get("object")
            
            if not event_type or not payment_object:
                logger.warning("Некорректные данные webhook")
                return None
            
            return {
                "event_type": event_type,
                "payment_id": payment_object.get("id"),
                "status": payment_object.get("status"),
                "amount": float(payment_object.get("amount", {}).get("value", 0)),
                "metadata": payment_object.get("metadata", {}),
                "created_at": payment_object.get("created_at"),
                "captured_at": payment_object.get("captured_at")
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return None


# Глобальный экземпляр сервиса
yookassa_service = YooKassaService()