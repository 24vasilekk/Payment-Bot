from aiogram import Dispatcher

from . import start
from . import payment
from . import status
from . import admin


def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    
    # Регистрируем обработчики в порядке приоритета
    start.register_handlers(dp)
    payment.register_handlers(dp)
    status.register_handlers(dp)
    admin.register_handlers(dp)