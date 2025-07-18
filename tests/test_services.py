import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram.types import User as TgUser
from services.subscription_service import SubscriptionService
from services.yookassa_service import YooKassaService
from services.notification_service import NotificationService
from services.telegram_service import TelegramService
from database.models import User, Payment, PaymentStatus, SubscriptionStatus


class TestSubscriptionService:
    """Тесты для SubscriptionService"""
    
    @pytest.fixture
    def subscription_service(self):
        """Экземпляр SubscriptionService для тестов"""
        return SubscriptionService()
    
    @pytest.fixture
    def mock_tg_user(self):
        """Мок Telegram пользователя"""
        return TgUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            last_name="User",
            username="test_user"
        )
    
    @pytest.mark.asyncio
    async def test_create_or_update_user_new(self, subscription_service, mock_tg_user):
        """Тест создания нового пользователя"""
        with patch('services.subscription_service.db') as mock_db:
            mock_db.get_user.return_value = None  # Пользователь не существует
            mock_db.save_user.return_value = True
            
            user = await subscription_service.create_or_update_user(mock_tg_user)
            
            assert user.user_id == 123456789
            assert user.username == "test_user"
            assert user.first_name == "Test"
            assert user.subscription_status == SubscriptionStatus.EXPIRED
            mock_db.save_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_or_update_user_existing(self, subscription_service, mock_tg_user):
        """Тест обновления существующего пользователя"""
        with patch('services.subscription_service.db') as mock_db:
            existing_user = User(
                user_id=123456789,
                username="old_username",
                first_name="Old",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            mock_db.get_user.return_value = existing_user
            mock_db.save_user.return_value = True
            
            user = await subscription_service.create_or_update_user(mock_tg_user)
            
            assert user.username == "test_user"  # Обновлено
            assert user.first_name == "Test"  # Обновлено
            assert user.subscription_status == SubscriptionStatus.ACTIVE  # Сохранено
            mock_db.save_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_subscription(self, subscription_service):
        """Тест активации подписки"""
        with patch('services.subscription_service.db') as mock_db, \
             patch('services.subscription_service.telegram_service') as mock_telegram, \
             patch('services.subscription_service.notification_service') as mock_notification:
            
            # Настраиваем мок пользователя
            user = User(
                user_id=123456789,
                subscription_status=SubscriptionStatus.EXPIRED
            )
            mock_db.get_user.return_value = user
            mock_db.save_user.return_value = True
            
            # Настраиваем мок сервисов
            mock_telegram.create_invite_link.return_value = "https://t.me/+test"
            mock_notification.send_subscription_activated.return_value = True
            
            # Создаем мок платежа
            payment = Payment(
                payment_id="test_123",
                user_id=123456789,
                amount=500.0
            )
            
            result = await subscription_service.activate_subscription(123456789, payment)
            
            assert result is True
            mock_db.save_user.assert_called_once()
            mock_telegram.create_invite_link.assert_called_once_with(123456789)
            mock_notification.send_subscription_activated.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extend_subscription(self, subscription_service):
        """Тест продления подписки"""
        with patch('services.subscription_service.db') as mock_db, \
             patch('services.subscription_service.notification_service') as mock_notification:
            
            # Пользователь с активной подпиской
            user = User(
                user_id=123456789,
                subscription_end=datetime.now() + timedelta(days=5),
                subscription_status=SubscriptionStatus.ACTIVE
            )
            mock_db.get_user.return_value = user
            mock_db.save_user.return_value = True
            mock_notification.send_subscription_extended.return_value = True
            
            result = await subscription_service.extend_subscription(123456789, 30, "manual")
            
            assert result is True
            # Проверяем, что подписка продлена
            assert user.subscription_end > datetime.now() + timedelta(days=30)
            mock_db.save_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_subscription(self, subscription_service):
        """Тест отмены подписки"""
        with patch('services.subscription_service.db') as mock_db, \
             patch('services.subscription_service.telegram_service') as mock_telegram, \
             patch('services.subscription_service.notification_service') as mock_notification:
            
            user = User(
                user_id=123456789,
                subscription_status=SubscriptionStatus.ACTIVE
            )
            mock_db.get_user.return_value = user
            mock_db.save_user.return_value = True
            mock_telegram.kick_user_from_channel.return_value = True
            mock_notification.send_subscription_cancelled.return_value = True
            
            result = await subscription_service.cancel_subscription(123456789, "test")
            
            assert result is True
            assert user.subscription_status == SubscriptionStatus.SUSPENDED
            assert user.is_active is False
            mock_telegram.kick_user_from_channel.assert_called_once_with(123456789)
    
    @pytest.mark.asyncio
    async def test_get_subscription_status(self, subscription_service):
        """Тест получения статуса подписки"""
        with patch('services.subscription_service.db') as mock_db:
            user = User(
                user_id=123456789,
                subscription_status=SubscriptionStatus.ACTIVE,
                subscription_end=datetime.now() + timedelta(days=15),
                total_payments=3,
                created_at=datetime.now() - timedelta(days=90)
            )
            user.is_subscription_active = True
            user.days_left = 15
            mock_db.get_user.return_value = user
            
            status = await subscription_service.get_subscription_status(123456789)
            
            assert status is not None
            assert status["is_active"] is True
            assert status["status"] == "active"
            assert status["days_left"] == 15
            assert status["total_payments"] == 3


class TestYooKassaService:
    """Тесты для YooKassaService"""
    
    @pytest.fixture
    def yookassa_service(self):
        """Экземпляр YooKassaService для тестов"""
        with patch('services.yookassa_service.YOOKASSA_SHOP_ID', 'test_shop'), \
             patch('services.yookassa_service.YOOKASSA_SECRET_KEY', 'test_secret'):
            return YooKassaService()
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, yookassa_service):
        """Тест успешного создания платежа"""
        mock_response_data = {
            "id": "yoo_payment_123",
            "confirmation": {
                "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=123"
            },
            "metadata": {"user_id": "123456789"}
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            payment = await yookassa_service.create_payment(
                amount=500.0,
                description="Test payment",
                user_id=123456789
            )
            
            assert payment is not None
            assert payment.yookassa_payment_id == "yoo_payment_123"
            assert payment.amount == 500.0
            assert payment.user_id == 123456789
            assert payment.status == PaymentStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_create_payment_failure(self, yookassa_service):
        """Тест неудачного создания платежа"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text.return_value = "Bad request"
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            payment = await yookassa_service.create_payment(
                amount=500.0,
                description="Test payment",
                user_id=123456789
            )
            
            assert payment is None
    
    @pytest.mark.asyncio
    async def test_get_payment_info(self, yookassa_service):
        """Тест получения информации о платеже"""
        mock_payment_data = {
            "id": "yoo_payment_123",
            "status": "succeeded",
            "amount": {"value": "500.00", "currency": "RUB"}
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_payment_data
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            payment_info = await yookassa_service.get_payment_info("yoo_payment_123")
            
            assert payment_info is not None
            assert payment_info["status"] == "succeeded"
            assert payment_info["amount"]["value"] == "500.00"
    
    def test_parse_webhook_notification(self, yookassa_service):
        """Тест парсинга webhook уведомления"""
        notification_data = {
            "event": "payment.succeeded",
            "object": {
                "id": "yoo_payment_123",
                "status": "succeeded",
                "amount": {"value": "500.00"},
                "metadata": {"user_id": "123456789"},
                "created_at": "2023-01-01T12:00:00Z",
                "captured_at": "2023-01-01T12:05:00Z"
            }
        }
        
        parsed_data = yookassa_service.parse_webhook_notification(notification_data)
        
        assert parsed_data is not None
        assert parsed_data["event_type"] == "payment.succeeded"
        assert parsed_data["payment_id"] == "yoo_payment_123"
        assert parsed_data["status"] == "succeeded"
        assert parsed_data["amount"] == 500.0
        assert parsed_data["metadata"]["user_id"] == "123456789"


class TestTelegramService:
    """Тесты для TelegramService"""
    
    @pytest.fixture
    def telegram_service(self):
        """Экземпляр TelegramService для тестов"""
        mock_bot = MagicMock()
        return TelegramService(mock_bot)
    
    @pytest.mark.asyncio
    async def test_create_invite_link(self, telegram_service):
        """Тест создания инвайт-ссылки"""
        mock_invite_link = MagicMock()
        mock_invite_link.invite_link = "https://t.me/+test_invite_link"
        
        telegram_service.bot.create_chat_invite_link.return_value = mock_invite_link
        
        invite_link = await telegram_service.create_invite_link(123456789)
        
        assert invite_link == "https://t.me/+test_invite_link"
        telegram_service.bot.create_chat_invite_link.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_kick_user_from_channel(self, telegram_service):
        """Тест исключения пользователя из канала"""
        telegram_service.bot.ban_chat_member.return_value = None
        telegram_service.bot.unban_chat_member.return_value = None
        
        result = await telegram_service.kick_user_from_channel(123456789)
        
        assert result is True
        telegram_service.bot.ban_chat_member.assert_called_once()
        telegram_service.bot.unban_chat_member.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message(self, telegram_service):
        """Тест отправки сообщения"""
        telegram_service.bot.send_message.return_value = None
        
        result = await telegram_service.send_message(123456789, "Test message")
        
        assert result is True
        telegram_service.bot.send_message.assert_called_once_with(
            chat_id=123456789,
            text="Test message",
            reply_markup=None,
            parse_mode="HTML"
        )
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, telegram_service):
        """Тест рассылки сообщений"""
        user_ids = [111, 222, 333]
        
        # Настраиваем моки: первый успешен, второй заблокирован, третий ошибка
        def side_effect(*args, **kwargs):
            chat_id = kwargs.get('chat_id') or args[0]
            if chat_id == 111:
                return None  # Успешно
            elif chat_id == 222:
                raise Exception("Blocked by user")  # Заблокирован
            else:
                raise Exception("Network error")  # Ошибка
        
        telegram_service.bot.send_message.side_effect = side_effect
        
        result = await telegram_service.broadcast_message(user_ids, "Broadcast message")
        
        assert result["total"] == 3
        assert result["sent"] == 1
        assert result["blocked"] == 1
        assert result["failed"] == 1


class TestNotificationService:
    """Тесты для NotificationService"""
    
    @pytest.fixture
    def notification_service(self):
        """Экземпляр NotificationService для тестов"""
        return NotificationService()
    
    @pytest.mark.asyncio
    async def test_send_welcome_message(self, notification_service):
        """Тест отправки приветственного сообщения"""
        with patch('services.notification_service.telegram_service') as mock_telegram:
            mock_telegram.send_message.return_value = True
            
            user = User(user_id=123456789, username="test_user")
            result = await notification_service.send_welcome_message(user)
            
            assert result is True
            mock_telegram.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_subscription_activated(self, notification_service):
        """Тест уведомления об активации подписки"""
        with patch('services.notification_service.telegram_service') as mock_telegram:
            mock_telegram.send_message.return_value = True
            
            user = User(
                user_id=123456789,
                subscription_end=datetime.now() + timedelta(days=30)
            )
            invite_link = "https://t.me/+test_link"
            
            result = await notification_service.send_subscription_activated(user, invite_link)
            
            assert result is True
            mock_telegram.send_message.assert_called_once()
            
            # Проверяем, что в сообщении есть ссылка
            call_args = mock_telegram.send_message.call_args[0]
            message_text = call_args[1]
            assert invite_link in message_text
    
    @pytest.mark.asyncio
    async def test_send_subscription_expired(self, notification_service):
        """Тест уведомления об истечении подписки"""
        with patch('services.notification_service.telegram_service') as mock_telegram:
            mock_telegram.send_message.return_value = True
            
            user = User(user_id=123456789)
            result = await notification_service.send_subscription_expired(user)
            
            assert result is True
            mock_telegram.send_message.assert_called_once()


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])