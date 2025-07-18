from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class PaymentStatus(Enum):
    """Статусы платежа"""
    PENDING = "pending"
    SUCCEEDED = "succeeded" 
    CANCELED = "canceled"
    FAILED = "failed"


class SubscriptionStatus(Enum):
    """Статусы подписки"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    TRIAL = "trial"


@dataclass
class User:
    """Модель пользователя"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    subscription_end: Optional[datetime] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.EXPIRED
    yookassa_customer_id: Optional[str] = None
    is_active: bool = True
    total_payments: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or self.username or f"User {self.user_id}"
    
    @property
    def is_subscription_active(self) -> bool:
        """Активна ли подписка"""
        return (
            self.subscription_end is not None
            and self.subscription_end > datetime.now()
            and self.subscription_status == SubscriptionStatus.ACTIVE
        )
    
    @property
    def days_left(self) -> int:
        """Количество дней до истечения подписки"""
        if not self.subscription_end:
            return 0
        delta = self.subscription_end - datetime.now()
        return max(0, delta.days)


@dataclass
class Payment:
    """Модель платежа"""
    id: Optional[int] = None
    user_id: int = 0
    payment_id: str = ""
    yookassa_payment_id: Optional[str] = None
    amount: float = 0.0
    currency: str = "RUB"
    status: PaymentStatus = PaymentStatus.PENDING
    description: Optional[str] = None
    confirmation_url: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def is_completed(self) -> bool:
        """Завершен ли платеж"""
        return self.status == PaymentStatus.SUCCEEDED
    
    @property
    def is_pending(self) -> bool:
        """Ожидает ли платеж обработки"""
        return self.status == PaymentStatus.PENDING


@dataclass
class InviteLink:
    """Модель инвайт-ссылки"""
    id: Optional[int] = None
    user_id: int = 0
    invite_link: str = ""
    expire_date: Optional[datetime] = None
    member_limit: int = 1
    is_used: bool = False
    created_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        """Истекла ли ссылка"""
        return (
            self.expire_date is not None
            and self.expire_date < datetime.now()
        )


@dataclass
class SubscriptionHistory:
    """История подписок пользователя"""
    id: Optional[int] = None
    user_id: int = 0
    payment_id: Optional[int] = None
    start_date: datetime = None
    end_date: datetime = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    amount_paid: float = 0.0
    created_at: Optional[datetime] = None