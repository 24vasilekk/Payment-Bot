from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """Состояния для процесса оплаты"""
    waiting_payment = State()
    payment_processing = State()
    payment_confirmation = State()


class AdminStates(StatesGroup):
    """Состояния для админских функций"""
    waiting_broadcast_message = State()
    waiting_user_id = State()
    confirming_action = State()


class SubscriptionStates(StatesGroup):
    """Состояния для управления подписками"""
    extending_subscription = State()
    canceling_subscription = State()