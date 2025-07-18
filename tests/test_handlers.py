import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram.types import Message, CallbackQuery, User as TgUser
from aiogram.fsm.context import FSMContext

from bot.handlers import start, payment, status
from database.models import User, SubscriptionStatus, Payment, PaymentStatus
from datetime import datetime, timedelta


class TestStartHandlers:
    """Тесты для обработчиков start.py"""
    
    @pytest.fixture
    def mock_message(self):
        """Мок объекта Message"""
        message = MagicMock(spec=Message)
        message.from_user = TgUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            username="test_user"
        )
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_callback(self):
        """Мок объекта CallbackQuery"""
        callback = MagicMock(spec=CallbackQuery)
        callback.from_user = TgUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            username="test_user"
        )
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock()
        return callback
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, mock_message):
        """Тест команды /start для нового пользователя"""
        with patch('bot.handlers.start.subscription_service') as mock_service, \
             patch('bot.handlers.start.notification_service') as mock_notification:
            
            # Настраиваем мок сервиса
            mock_user = User(
                user_id=123456789,
                username="test_user",
                first_name="Test",
                subscription_status=SubscriptionStatus.EXPIRED
            )
            mock_service.create_or_update_user.return_value = mock_user
            mock_notification.send_welcome_message.return_value = True
            
            # Вызываем обработчик
            await start.start_command(mock_message)
            
            # Проверяем вызовы
            mock_service.create_or_update_user.assert_called_once()
            mock_notification.send_welcome_message.assert_called_once_with(mock_user)
    
    @pytest.mark.asyncio
    async def test_start_command_active_user(self, mock_message):
        """Тест команды /start для пользователя с активной подпиской"""
        with patch('bot.handlers.start.subscription_service') as mock_service:
            
            # Настраиваем мок пользователя с активной подпиской
            mock_user = User(
                user_id=123456789,
                username="test_user",
                first_name="Test",
                subscription_status=SubscriptionStatus.ACTIVE,
                subscription_end=datetime.now() + timedelta(days=30)
            )
            mock_user.is_subscription_active = True
            mock_user.days_left = 30
            mock_service.create_or_update_user.return_value = mock_user
            
            # Вызываем обработчик
            await start.start_command(mock_message)
            
            # Проверяем, что отправлено сообщение о активной подписке
            mock_message.answer.assert_called_once()
            args = mock_message.answer.call_args[0]
            assert "активна до" in args[0]
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_message):
        """Тест команды /help"""
        with patch('bot.handlers.start.notification_service') as mock_notification:
            mock_notification.send_help_message.return_value = True
            
            await start.help_command(mock_message)
            
            mock_notification.send_help_message.assert_called_once_with(
                123456789, "general"
            )
    
    @pytest.mark.asyncio
    async def test_help_callback(self, mock_callback):
        """Тест callback кнопки помощи"""
        with patch('bot.handlers.start.notification_service') as mock_notification:
            mock_notification.send_help_message.return_value = True
            
            await start.help_callback(mock_callback)
            
            mock_notification.send_help_message.assert_called_once()
            mock_callback.answer.assert_called_once_with("📖 Справка отправлена!")


class TestPaymentHandlers:
    """Тесты для обработчиков payment.py"""
    
    @pytest.fixture
    def mock_message(self):
        """Мок объекта Message"""
        message = MagicMock(spec=Message)
        message.from_user = TgUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            username="test_user"
        )
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_state(self):
        """Мок объекта FSMContext"""
        state = MagicMock(spec=FSMContext)
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()
        state.clear = AsyncMock()
        return state
    
    @pytest.mark.asyncio
    async def test_pay_command_success(self, mock_message, mock_state):
        """Тест успешного создания платежа"""
        with patch('bot.handlers.payment.subscription_service') as mock_sub_service, \
             patch('bot.handlers.payment.yookassa_service') as mock_yookassa, \
             patch('bot.handlers.payment.db') as mock_db:
            
            # Настраиваем моки
            mock_user = User(
                user_id=123456789,
                subscription_status=SubscriptionStatus.EXPIRED
            )
            mock_user.is_subscription_active = False
            mock_sub_service.create_or_update_user.return_value = mock_user
            
            mock_payment = Payment(
                payment_id="test_123",
                yookassa_payment_id="yoo_123",
                confirmation_url="https://test.com",
                amount=500.0
            )
            mock_yookassa.create_payment.return_value = mock_payment
            mock_db.save_payment.return_value = True
            
            # Вызываем обработчик
            await payment.pay_command(mock_message, mock_state)
            
            # Проверяем вызовы
            mock_yookassa.create_payment.assert_called_once()
            mock_db.save_payment.assert_called_once_with(mock_payment)
            mock_state.update_data.assert_called_once()
            mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pay_command_active_subscription(self, mock_message, mock_state):
        """Тест команды /pay для пользователя с активной подпиской"""
        with patch('bot.handlers.payment.subscription_service') as mock_service:
            
            # Пользователь с активной подпиской
            mock_user = User(
                user_id=123456789,
                subscription_status=SubscriptionStatus.ACTIVE,
                subscription_end=datetime.now() + timedelta(days=15)
            )
            mock_user.is_subscription_active = True
            mock_user.days_left = 15
            mock_service.create_or_update_user.return_value = mock_user
            
            await payment.pay_command(mock_message, mock_state)
            
            # Проверяем, что отправлено сообщение о существующей подписке
            mock_message.answer.assert_called_once()
            args = mock_message.answer.call_args[0]
            assert "уже есть активная подписка" in args[0]
    
    @pytest.mark.asyncio
    async def test_check_payment_callback_success(self):
        """Тест успешной проверки платежа"""
        mock_callback = MagicMock(spec=CallbackQuery)
        mock_callback.data = "check_payment:test_123"
        mock_callback.from_user = TgUser(id=123456789, is_bot=False, first_name="Test")
        mock_callback.answer = AsyncMock()
        mock_callback.message = MagicMock()
        mock_callback.message.edit_text = AsyncMock()
        
        mock_state = MagicMock(spec=FSMContext)
        mock_state.clear = AsyncMock()
        
        with patch('bot.handlers.payment.db') as mock_db, \
             patch('bot.handlers.payment.yookassa_service') as mock_yookassa, \
             patch('bot.handlers.payment.subscription_service') as mock_sub_service:
            
            # Настраиваем моки
            mock_payment = Payment(
                payment_id="test_123",
                yookassa_payment_id="yoo_123",
                user_id=123456789,
                amount=500.0,
                status=PaymentStatus.PENDING
            )
            mock_db.get_payment.return_value = mock_payment
            
            mock_yookassa_payment = {"status": "succeeded"}
            mock_yookassa.get_payment_info.return_value = mock_yookassa_payment
            
            mock_sub_service.activate_subscription.return_value = True
            mock_db.save_payment.return_value = True
            
            # Вызываем обработчик
            await payment.check_payment_callback(mock_callback, mock_state)
            
            # Проверяем результат
            mock_sub_service.activate_subscription.assert_called_once()
            mock_callback.message.edit_text.assert_called_once()
            mock_state.clear.assert_called_once()


class TestStatusHandlers:
    """Тесты для обработчиков status.py"""
    
    @pytest.fixture
    def mock_message(self):
        """Мок объекта Message"""
        message = MagicMock(spec=Message)
        message.from_user = TgUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            username="test_user"
        )
        message.answer = AsyncMock()
        return message
    
    @pytest.mark.asyncio
    async def test_status_command_active_subscription(self, mock_message):
        """Тест команды /status для активной подписки"""
        with patch('bot.handlers.status.subscription_service') as mock_service, \
             patch('bot.handlers.status.telegram_service') as mock_telegram:
            
            # Настраиваем мок статуса
            mock_status = {
                "is_active": True,
                "status": "active",
                "end_date": datetime.now() + timedelta(days=15),
                "days_left": 15,
                "total_payments": 2,
                "created_at": datetime.now() - timedelta(days=60)
            }
            mock_service.get_subscription_status.return_value = mock_status
            mock_telegram.check_user_in_channel.return_value = True
            
            await status.status_command(mock_message)
            
            # Проверяем вызовы
            mock_service.get_subscription_status.assert_called_once_with(123456789)
            mock_message.answer.assert_called_once()
            
            # Проверяем содержимое ответа
            args = mock_message.answer.call_args[0]
            assert "Активна" in args[0]
            assert "15" in args[0]  # Дни до истечения
    
    @pytest.mark.asyncio
    async def test_status_command_expired_subscription(self, mock_message):
        """Тест команды /status для истекшей подписки"""
        with patch('bot.handlers.status.subscription_service') as mock_service:
            
            # Настраиваем мок статуса
            mock_status = {
                "is_active": False,
                "status": "expired",
                "end_date": datetime.now() - timedelta(days=5),
                "days_left": 0,
                "total_payments": 1,
                "created_at": datetime.now() - timedelta(days=60)
            }
            mock_service.get_subscription_status.return_value = mock_status
            
            await status.status_command(mock_message)
            
            # Проверяем содержимое ответа
            args = mock_message.answer.call_args[0]
            assert "Истекла" in args[0]
    
    @pytest.mark.asyncio
    async def test_status_command_no_user(self, mock_message):
        """Тест команды /status для несуществующего пользователя"""
        with patch('bot.handlers.status.subscription_service') as mock_service:
            
            mock_service.get_subscription_status.return_value = None
            
            await status.status_command(mock_message)
            
            # Проверяем содержимое ответа
            args = mock_message.answer.call_args[0]
            assert "не найдена" in args[0]
    
    @pytest.mark.asyncio
    async def test_info_command(self, mock_message):
        """Тест команды /info"""
        with patch('bot.handlers.status.telegram_service') as mock_telegram, \
             patch('bot.handlers.status.subscription_service') as mock_service:
            
            mock_channel_info = {
                "member_count": 1500,
                "title": "Test Channel"
            }
            mock_telegram.get_channel_info.return_value = mock_channel_info
            
            await status.info_command(mock_message)
            
            # Проверяем вызовы
            mock_telegram.get_channel_info.assert_called_once()
            mock_message.answer.assert_called_once()
            
            # Проверяем содержимое ответа
            args = mock_message.answer.call_args[0]
            assert "1500" in args[0]  # Количество участников
            assert "Test Channel" in args[0]  # Название канала
    
    @pytest.mark.asyncio
    async def test_myid_command(self, mock_message):
        """Тест команды /myid"""
        await status.myid_command(mock_message)
        
        # Проверяем, что ответ содержит ID пользователя
        mock_message.answer.assert_called_once()
        args = mock_message.answer.call_args[0]
        assert "123456789" in args[0]
        assert "test_user" in args[0]


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])