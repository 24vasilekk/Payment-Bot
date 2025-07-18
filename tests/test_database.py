import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корневую директорию в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import Database
from database.models import User, Payment, PaymentStatus, SubscriptionStatus


class TestDatabase:
    """Тесты для работы с базой данных"""
    
    @pytest.fixture
    async def temp_db(self):
        """Создание временной базы данных для тестов"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            db_path = temp_file.name
        
        db = Database(db_path)
        await db.init_database()
        
        yield db
        
        # Очистка после теста
        os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, temp_db):
        """Тест инициализации базы данных"""
        # Проверяем, что база данных создана
        assert os.path.exists(temp_db.db_path)
        
        # Проверяем, что таблицы созданы
        async with temp_db._get_connection() as conn:
            tables = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            table_names = [row[0] for row in await tables.fetchall()]
            
            expected_tables = ['users', 'payments', 'invite_links', 'subscription_history']
            for table in expected_tables:
                assert table in table_names
    
    @pytest.mark.asyncio
    async def test_user_creation_and_retrieval(self, temp_db):
        """Тест создания и получения пользователя"""
        # Создаем тестового пользователя
        user = User(
            user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_end=datetime.now() + timedelta(days=30)
        )
        
        # Сохраняем пользователя
        result = await temp_db.save_user(user)
        assert result is True
        
        # Получаем пользователя
        retrieved_user = await temp_db.get_user(123456789)
        assert retrieved_user is not None
        assert retrieved_user.user_id == 123456789
        assert retrieved_user.username == "test_user"
        assert retrieved_user.first_name == "Test"
        assert retrieved_user.subscription_status == SubscriptionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_user_update(self, temp_db):
        """Тест обновления пользователя"""
        # Создаем пользователя
        user = User(
            user_id=123456789,
            username="test_user",
            first_name="Test"
        )
        await temp_db.save_user(user)
        
        # Обновляем пользователя
        user.first_name = "Updated"
        user.subscription_status = SubscriptionStatus.ACTIVE
        result = await temp_db.save_user(user)
        assert result is True
        
        # Проверяем обновление
        updated_user = await temp_db.get_user(123456789)
        assert updated_user.first_name == "Updated"
        assert updated_user.subscription_status == SubscriptionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_payment_creation_and_retrieval(self, temp_db):
        """Тест создания и получения платежа"""
        # Сначала создаем пользователя
        user = User(user_id=123456789, username="test_user")
        await temp_db.save_user(user)
        
        # Создаем платеж
        payment = Payment(
            user_id=123456789,
            payment_id="test_payment_123",
            yookassa_payment_id="yoo_123",
            amount=500.0,
            status=PaymentStatus.PENDING,
            description="Test payment"
        )
        
        # Сохраняем платеж
        result = await temp_db.save_payment(payment)
        assert result is True
        
        # Получаем платеж
        retrieved_payment = await temp_db.get_payment("test_payment_123")
        assert retrieved_payment is not None
        assert retrieved_payment.payment_id == "test_payment_123"
        assert retrieved_payment.user_id == 123456789
        assert retrieved_payment.amount == 500.0
        assert retrieved_payment.status == PaymentStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_expired_users_retrieval(self, temp_db):
        """Тест получения пользователей с истекшей подпиской"""
        # Создаем пользователей с разными статусами
        user1 = User(
            user_id=111,
            username="expired_user",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_end=datetime.now() - timedelta(days=1)  # Истекшая
        )
        
        user2 = User(
            user_id=222,
            username="active_user",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_end=datetime.now() + timedelta(days=30)  # Активная
        )
        
        user3 = User(
            user_id=333,
            username="no_subscription",
            subscription_status=SubscriptionStatus.EXPIRED
        )
        
        await temp_db.save_user(user1)
        await temp_db.save_user(user2)
        await temp_db.save_user(user3)
        
        # Получаем истекших пользователей
        expired_users = await temp_db.get_expired_users()
        
        # Должен быть только user1
        assert len(expired_users) == 1
        assert expired_users[0].user_id == 111
    
    @pytest.mark.asyncio
    async def test_user_properties(self, temp_db):
        """Тест свойств модели User"""
        user = User(
            user_id=123,
            first_name="John",
            last_name="Doe",
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_end=datetime.now() + timedelta(days=15)
        )
        
        # Тест full_name
        assert user.full_name == "John Doe"
        
        # Тест is_subscription_active
        assert user.is_subscription_active is True
        
        # Тест days_left
        assert user.days_left == 15
        
        # Тест с истекшей подпиской
        user.subscription_end = datetime.now() - timedelta(days=1)
        assert user.is_subscription_active is False
        assert user.days_left == 0
    
    @pytest.mark.asyncio
    async def test_payment_properties(self, temp_db):
        """Тест свойств модели Payment"""
        payment = Payment(
            payment_id="test_123",
            status=PaymentStatus.SUCCEEDED,
            amount=1000.0
        )
        
        assert payment.is_completed is True
        assert payment.is_pending is False
        
        payment.status = PaymentStatus.PENDING
        assert payment.is_completed is False
        assert payment.is_pending is True
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, temp_db):
        """Тест обработки ошибок базы данных"""
        # Попытка получить несуществующего пользователя
        user = await temp_db.get_user(999999)
        assert user is None
        
        # Попытка получить несуществующий платеж
        payment = await temp_db.get_payment("nonexistent")
        assert payment is None
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, temp_db):
        """Тест конкурентного доступа к базе данных"""
        users = [
            User(user_id=i, username=f"user_{i}")
            for i in range(100, 110)
        ]
        
        # Одновременное сохранение пользователей
        tasks = [temp_db.save_user(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверяем, что все операции успешны
        for result in results:
            assert result is True or isinstance(result, Exception) is False
        
        # Проверяем, что все пользователи сохранены
        for user in users:
            retrieved = await temp_db.get_user(user.user_id)
            assert retrieved is not None
            assert retrieved.user_id == user.user_id


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])