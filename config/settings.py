import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Базовая директория проекта
BASE_DIR = Path(__file__).parent.parent

# Telegram Bot настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@your_channel')
ADMIN_IDS = []
if os.getenv('ADMIN_IDS'):
    try:
        ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS').split(',') if x.strip()]
    except ValueError:
        print("❌ Ошибка в ADMIN_IDS. Используйте формат: 123456789,987654321")
        ADMIN_IDS = []

# ЮKassa настройки  
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')
YOOKASSA_BASE_URL = 'https://api.yookassa.ru/v3'

# Подписка настройки
SUBSCRIPTION_PRICE = float(os.getenv('SUBSCRIPTION_PRICE', '500'))
SUBSCRIPTION_DURATION_DAYS = int(os.getenv('SUBSCRIPTION_DURATION_DAYS', '30'))
TRIAL_PERIOD_DAYS = int(os.getenv('TRIAL_PERIOD_DAYS', '0'))

# База данных
DATABASE_PATH = BASE_DIR / 'data' / 'users.db'

# Webhook настройки
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'localhost')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8080'))
WEBHOOK_PATH = '/webhook/yookassa'
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Логирование
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = BASE_DIR / 'logs'

# Создание директорий
LOG_DIR.mkdir(exist_ok=True)
DATABASE_PATH.parent.mkdir(exist_ok=True)

# Проверка обязательных переменных
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден в .env файле")

if not ADMIN_IDS:
    print("⚠️ ADMIN_IDS не настроены - админские функции недоступны")

# Временно отключаем проверку ЮKassa для тестирования
if not YOOKASSA_SHOP_ID or YOOKASSA_SHOP_ID == 'test_shop_id':
    print("⚠️ ЮKassa не настроена - используется тестовый режим")

# Дополнительные настройки
INVITE_LINK_EXPIRE_HOURS = int(os.getenv('INVITE_LINK_EXPIRE_HOURS', '24'))
CHECK_SUBSCRIPTIONS_INTERVAL_MINUTES = int(os.getenv('CHECK_SUBSCRIPTIONS_INTERVAL_MINUTES', '60'))
MAX_PAYMENT_ATTEMPTS = int(os.getenv('MAX_PAYMENT_ATTEMPTS', '3'))

# Сообщения
MESSAGES = {
    'welcome': """
🔐 <b>Добро пожаловать!</b>

Для доступа к каналу {channel_id} необходимо оформить подписку.

💰 <b>Стоимость:</b> {price} руб/месяц
⚡ <b>Мгновенный доступ</b> после оплаты

Используйте /pay для оплаты подписки
    """.strip(),
    
    'payment_success': """
✅ <b>Оплата прошла успешно!</b>

📅 Подписка активна до: {subscription_end}
🔗 Ссылка для входа: {invite_link}

Спасибо за оплату! 🎉
    """.strip(),
    
    'subscription_expired': """
❌ <b>Ваша подписка истекла!</b>

Доступ к каналу приостановлен.
Используйте /pay для продления подписки.
    """.strip(),
    
    'payment_failed': """
❌ <b>Оплата не прошла</b>

Попробуйте еще раз или обратитесь в поддержку.
    """.strip()
}