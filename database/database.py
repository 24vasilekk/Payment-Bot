import aiosqlite
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from config.settings import DATABASE_PATH
from database.models import User, Payment, PaymentStatus, SubscriptionStatus

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        
    async def _get_connection(self):
        """Получение соединения с базой данных"""
        return aiosqlite.connect(self.db_path)
        
    async def init_database(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Включаем поддержку внешних ключей
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Создание таблицы пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    subscription_end TIMESTAMP,
                    subscription_status TEXT DEFAULT 'expired',
                    yookassa_customer_id TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    total_payments INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создание таблицы платежей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    payment_id TEXT UNIQUE NOT NULL,
                    yookassa_payment_id TEXT UNIQUE,
                    amount DECIMAL(10,2) NOT NULL,
                    currency TEXT DEFAULT 'RUB',
                    status TEXT DEFAULT 'pending',
                    description TEXT,
                    confirmation_url TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Создание таблицы инвайт-ссылок
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invite_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    invite_link TEXT NOT NULL,
                    expire_date TIMESTAMP,
                    member_limit INTEGER DEFAULT 1,
                    is_used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Создание таблицы истории подписок
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscription_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    payment_id INTEGER,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'active',
                    amount_paid DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (payment_id) REFERENCES payments (id)
                )
            """)
            
            # Создание индексов для оптимизации
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription_end ON users(subscription_end)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
            
            await db.commit()
            logger.info("База данных инициализирована успешно")
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return User(
                        user_id=row['user_id'],
                        username=row['username'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        subscription_end=datetime.fromisoformat(row['subscription_end']) if row['subscription_end'] else None,
                        subscription_status=SubscriptionStatus(row['subscription_status']),
                        yookassa_customer_id=row['yookassa_customer_id'],
                        is_active=bool(row['is_active']),
                        total_payments=row['total_payments'],
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                    )
                return None
    
    async def save_user(self, user: User) -> bool:
        """Сохранить пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                user.updated_at = datetime.now()
                
                await db.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, subscription_end, 
                     subscription_status, yookassa_customer_id, is_active, 
                     total_payments, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 
                           COALESCE((SELECT created_at FROM users WHERE user_id = ?), CURRENT_TIMESTAMP), 
                           ?)
                """, (
                    user.user_id, user.username, user.first_name, user.last_name,
                    user.subscription_end.isoformat() if user.subscription_end else None,
                    user.subscription_status.value, user.yookassa_customer_id,
                    user.is_active, user.total_payments, user.user_id,
                    user.updated_at.isoformat()
                ))
                
                await db.commit()
                logger.info(f"Пользователь {user.user_id} сохранен")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя {user.user_id}: {e}")
            return False
    
    async def get_expired_users(self) -> List[User]:
        """Получить пользователей с истекшей подпиской"""
        users = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users 
                WHERE subscription_end < ? 
                AND subscription_status = 'active'
                AND is_active = 1
            """, (datetime.now().isoformat(),)) as cursor:
                
                async for row in cursor:
                    users.append(User(
                        user_id=row['user_id'],
                        username=row['username'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        subscription_end=datetime.fromisoformat(row['subscription_end']) if row['subscription_end'] else None,
                        subscription_status=SubscriptionStatus(row['subscription_status']),
                        yookassa_customer_id=row['yookassa_customer_id'],
                        is_active=bool(row['is_active']),
                        total_payments=row['total_payments']
                    ))
        
        return users
    
    async def save_payment(self, payment: Payment) -> bool:
        """Сохранить платеж"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                payment.updated_at = datetime.now()
                
                await db.execute("""
                    INSERT OR REPLACE INTO payments 
                    (user_id, payment_id, yookassa_payment_id, amount, currency, 
                     status, description, confirmation_url, metadata, 
                     created_at, updated_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 
                           COALESCE((SELECT created_at FROM payments WHERE payment_id = ?), CURRENT_TIMESTAMP),
                           ?, ?)
                """, (
                    payment.user_id, payment.payment_id, payment.yookassa_payment_id,
                    payment.amount, payment.currency, payment.status.value,
                    payment.description, payment.confirmation_url,
                    str(payment.metadata) if payment.metadata else None,
                    payment.payment_id, payment.updated_at.isoformat(),
                    payment.completed_at.isoformat() if payment.completed_at else None
                ))
                
                await db.commit()
                logger.info(f"Платеж {payment.payment_id} сохранен")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения платежа {payment.payment_id}: {e}")
            return False
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Получить платеж по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return Payment(
                        id=row['id'],
                        user_id=row['user_id'],
                        payment_id=row['payment_id'],
                        yookassa_payment_id=row['yookassa_payment_id'],
                        amount=row['amount'],
                        currency=row['currency'],
                        status=PaymentStatus(row['status']),
                        description=row['description'],
                        confirmation_url=row['confirmation_url'],
                        metadata=eval(row['metadata']) if row['metadata'] else None,
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                        completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
                    )
                return None


# Глобальный экземпляр базы данных
db = Database()

async def init_database():
    """Инициализация базы данных"""
    await db.init_database()