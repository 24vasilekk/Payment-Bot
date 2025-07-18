import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config.settings import SUBSCRIPTION_PRICE, CHANNEL_ID
from services.yookassa_service import yookassa_service
from services.subscription_service import subscription_service
from services.notification_service import notification_service
from database.database import db
from database.models import PaymentStatus
from bot.keyboards.inline import get_payment_keyboard, get_subscription_keyboard
from bot.states.payment_states import PaymentStates
from utils.logger import payment_logger

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("pay"))
async def pay_command(message: Message, state: FSMContext):
    """Обработчик команды /pay"""
    try:
        user_id = message.from_user.id
        
        # Создаем или обновляем пользователя
        user = await subscription_service.create_or_update_user(message.from_user)
        
        # Проверяем, есть ли уже активная подписка
        if user.is_subscription_active:
            await message.answer(
                f"✅ У вас уже есть активная подписка!\n\n"
                f"📅 Действует до: {user.subscription_end.strftime('%d.%m.%Y %H:%M')}\n"
                f"⏰ Осталось дней: {user.days_left}\n\n"
                f"💡 Вы можете продлить подписку заранее - новый период добавится к текущему.",
                reply_markup=get_subscription_keyboard()
            )
            return
        
        # Создаем платеж в YooKassa
        payment = await yookassa_service.create_payment(
            amount=SUBSCRIPTION_PRICE,
            description=f"Подписка на канал {CHANNEL_ID}",
            user_id=user_id,
            return_url=f"https://t.me/{(await message.bot.get_me()).username}"
        )
        
        if payment:
            # Сохраняем платеж в базу данных
            await db.save_payment(payment)
            
            # Сохраняем данные в состоянии
            await state.update_data(payment_id=payment.payment_id)
            await state.set_state(PaymentStates.waiting_payment)
            
            # Отправляем сообщение с кнопками оплаты
            keyboard = get_payment_keyboard(payment.payment_id, payment.confirmation_url)
            
            await message.answer(
                f"💰 <b>Счет для оплаты создан!</b>\n\n"
                f"💳 Сумма: {SUBSCRIPTION_PRICE} руб\n"
                f"📅 Срок подписки: 30 дней\n"
                f"📢 Канал: {CHANNEL_ID}\n\n"
                f"Нажмите кнопку для оплаты:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            logger.info(f"Создан платеж {payment.payment_id} для пользователя {user_id}")
            
        else:
            await message.answer(
                "❌ Ошибка создания платежа. Попробуйте позже или обратитесь в поддержку.",
                reply_markup=get_subscription_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике /pay: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_subscription_keyboard()
        )


@router.callback_query(F.data == "pay_subscription")
async def pay_subscription_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки оплаты подписки"""
    try:
        # Имитируем команду /pay
        message = callback.message
        message.from_user = callback.from_user
        await pay_command(message, state)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в pay_subscription callback: {e}")
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик проверки статуса платежа"""
    try:
        payment_id = callback.data.split(":", 1)[1]
        user_id = callback.from_user.id
        
        # Получаем платеж из базы данных
        payment = await db.get_payment(payment_id)
        
        if not payment:
            await callback.answer("❌ Платеж не найден", show_alert=True)
            return
        
        if payment.user_id != user_id:
            await callback.answer("❌ Это не ваш платеж", show_alert=True)
            return
        
        # Проверяем статус в YooKassa
        if payment.yookassa_payment_id:
            yookassa_payment = await yookassa_service.get_payment_info(payment.yookassa_payment_id)
            
            if yookassa_payment:
                status = yookassa_payment.get("status")
                
                if status == "succeeded":
                    # Платеж успешен - активируем подписку
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.completed_at = payment.updated_at
                    await db.save_payment(payment)
                    
                    # Активируем подписку
                    success = await subscription_service.activate_subscription(user_id, payment)
                    
                    if success:
                        await callback.message.edit_text(
                            "✅ <b>Оплата прошла успешно!</b>\n\n"
                            "Подписка активирована. Проверьте личные сообщения - туда отправлена ссылка для входа в канал.",
                            parse_mode="HTML"
                        )
                        payment_logger.payment_succeeded(user_id, payment_id, payment.amount)
                    else:
                        await callback.message.edit_text(
                            "⚠️ Оплата прошла, но возникла ошибка активации подписки.\n"
                            "Обратитесь в поддержку для решения вопроса."
                        )
                    
                    await state.clear()
                    
                elif status == "canceled":
                    payment.status = PaymentStatus.CANCELED
                    await db.save_payment(payment)
                    
                    await callback.message.edit_text(
                        "❌ Платеж отменен.\n\nВы можете создать новый платеж с помощью команды /pay",
                        reply_markup=get_subscription_keyboard()
                    )
                    payment_logger.payment_failed(user_id, payment_id, "canceled")
                    await state.clear()
                    
                elif status == "waiting_for_capture":
                    await callback.answer("💳 Платеж обрабатывается банком...")
                    
                else:
                    await callback.answer("⏳ Платеж еще обрабатывается...")
            else:
                await callback.answer("❌ Ошибка проверки платежа", show_alert=True)
        else:
            await callback.answer("⏳ Платеж еще не создан в системе", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка проверки платежа: {e}")
        await callback.answer("❌ Ошибка проверки платежа", show_alert=True)


@router.callback_query(F.data.startswith("cancel_payment:"))
async def cancel_payment_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены платежа"""
    try:
        payment_id = callback.data.split(":", 1)[1]
        user_id = callback.from_user.id
        
        # Получаем платеж из базы данных
        payment = await db.get_payment(payment_id)
        
        if payment and payment.user_id == user_id:
            # Отменяем платеж в YooKassa если возможно
            if payment.yookassa_payment_id and payment.status == PaymentStatus.PENDING:
                await yookassa_service.cancel_payment(payment.yookassa_payment_id)
            
            # Обновляем статус в базе
            payment.status = PaymentStatus.CANCELED
            await db.save_payment(payment)
            
            await callback.message.edit_text(
                "❌ Платеж отменен.\n\nВы можете создать новый платеж с помощью команды /pay",
                reply_markup=get_subscription_keyboard()
            )
            
            payment_logger.payment_failed(user_id, payment_id, "user_canceled")
            
        await state.clear()
        await callback.answer("Платеж отменен")
        
    except Exception as e:
        logger.error(f"Ошибка отмены платежа: {e}")
        await callback.answer("❌ Ошибка отмены платежа", show_alert=True)


@router.callback_query(F.data.startswith("refresh_payment:"))
async def refresh_payment_callback(callback: CallbackQuery):
    """Обработчик обновления статуса платежа"""
    try:
        payment_id = callback.data.split(":", 1)[1]
        
        # Перенаправляем на проверку платежа
        callback.data = f"check_payment:{payment_id}"
        await check_payment_callback(callback, None)
        
    except Exception as e:
        logger.error(f"Ошибка обновления платежа: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)