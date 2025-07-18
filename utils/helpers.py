import re
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def validate_telegram_token(token: str) -> bool:
    """
    Проверка валидности токена Telegram бота
    
    Args:
        token: Токен бота
        
    Returns:
        True если токен валиден, False если нет
    """
    if not token:
        return False
    
    # Паттерн токена: число:строка из букв, цифр, дефисов и подчеркиваний
    pattern = r'^\d+:[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, token))


def validate_channel_id(channel_id: str) -> bool:
    """
    Проверка валидности ID канала
    
    Args:
        channel_id: ID или username канала
        
    Returns:
        True если ID валиден, False если нет
    """
    if not channel_id:
        return False
    
    # Может быть числовым ID или username начинающимся с @
    if channel_id.startswith('@'):
        # Username должен содержать только буквы, цифры и подчеркивания
        username = channel_id[1:]
        return bool(re.match(r'^[A-Za-z0-9_]+$', username)) and len(username) >= 5
    else:
        # Числовой ID (может быть отрицательным для каналов)
        try:
            int(channel_id)
            return True
        except ValueError:
            return False


def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """
    Форматирование даты и времени
    
    Args:
        dt: Объект datetime
        format_type: Тип форматирования ("full", "date", "time", "short")
        
    Returns:
        Отформатированная строка
    """
    if not dt:
        return "Не указано"
    
    formats = {
        "full": "%d.%m.%Y в %H:%M:%S",
        "date": "%d.%m.%Y",
        "time": "%H:%M",
        "short": "%d.%m %H:%M"
    }
    
    format_str = formats.get(format_type, formats["full"])
    return dt.strftime(format_str)


def format_currency(amount: float, currency: str = "RUB") -> str:
    """
    Форматирование суммы с валютой
    
    Args:
        amount: Сумма
        currency: Валюта
        
    Returns:
        Отформатированная строка
    """
    currency_symbols = {
        "RUB": "₽",
        "USD": "$",
        "EUR": "€"
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if amount == int(amount):
        return f"{int(amount)} {symbol}"
    else:
        return f"{amount:.2f} {symbol}"


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Парсинг строки с длительностью в timedelta
    
    Args:
        duration_str: Строка типа "30d", "2h", "45m"
        
    Returns:
        Объект timedelta или None
    """
    if not duration_str:
        return None
    
    # Паттерн: число + единица измерения
    pattern = r'^(\d+)([dhms])$'
    match = re.match(pattern, duration_str.lower())
    
    if not match:
        return None
    
    value = int(match.group(1))
    unit = match.group(2)
    
    unit_map = {
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }
    
    kwargs = {unit_map[unit]: value}
    return timedelta(**kwargs)


def generate_payment_id() -> str:
    """
    Генерация уникального ID платежа
    
    Returns:
        Уникальный ID платежа
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(4)
    return f"pay_{timestamp}_{random_part}"


def generate_invite_code(length: int = 8) -> str:
    """
    Генерация кода приглашения
    
    Args:
        length: Длина кода
        
    Returns:
        Код приглашения
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_user_data(user_id: int, additional_data: str = "") -> str:
    """
    Хеширование пользовательских данных
    
    Args:
        user_id: ID пользователя
        additional_data: Дополнительные данные
        
    Returns:
        Хеш строки
    """
    data = f"{user_id}:{additional_data}:{datetime.now().date()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Безопасный парсинг JSON
    
    Args:
        json_str: JSON строка
        default: Значение по умолчанию при ошибке
        
    Returns:
        Распарсенные данные или значение по умолчанию
    """
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse JSON: {json_str}")
        return default


def safe_json_dumps(data: Any) -> str:
    """
    Безопасная сериализация в JSON
    
    Args:
        data: Данные для сериализации
        
    Returns:
        JSON строка
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize to JSON: {e}")
        return "{}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезание текста до заданной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        Обрезанный текст
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_user_mention(text: str) -> Optional[int]:
    """
    Извлечение ID пользователя из упоминания или команды
    
    Args:
        text: Текст с упоминанием
        
    Returns:
        ID пользователя или None
    """
    if not text:
        return None
    
    # Ищем числовой ID
    numbers = re.findall(r'\b\d+\b', text)
    if numbers:
        try:
            return int(numbers[0])
        except ValueError:
            pass
    
    return None


def validate_url(url: str) -> bool:
    """
    Проверка валидности URL
    
    Args:
        url: URL для проверки
        
    Returns:
        True если URL валиден, False если нет
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """
    Форматирование размера файла
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированная строка
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_time_until_expiry(expiry_date: datetime) -> str:
    """
    Получение строки с временем до истечения
    
    Args:
        expiry_date: Дата истечения
        
    Returns:
        Строка с описанием времени
    """
    if not expiry_date:
        return "Не указано"
    
    now = datetime.now()
    
    if expiry_date <= now:
        return "Истекло"
    
    diff = expiry_date - now
    
    if diff.days > 0:
        return f"{diff.days} дн."
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч."
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин."
    else:
        return "Менее минуты"


def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """
    Создание текстового прогресс-бара
    
    Args:
        current: Текущее значение
        total: Общее значение
        length: Длина прогресс-бара
        
    Returns:
        Прогресс-бар в виде строки
    """
    if total == 0:
        return "█" * length
    
    progress = min(current / total, 1.0)
    filled_length = int(length * progress)
    
    bar = "█" * filled_length + "░" * (length - filled_length)
    percentage = int(progress * 100)
    
    return f"{bar} {percentage}%"


def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов для Markdown
    
    Args:
        text: Исходный текст
        
    Returns:
        Экранированный текст
    """
    if not text:
        return ""
    
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_user_info(user_id: int, username: str = None, first_name: str = None) -> str:
    """
    Форматирование информации о пользователе
    
    Args:
        user_id: ID пользователя
        username: Username пользователя
        first_name: Имя пользователя
        
    Returns:
        Отформатированная строка
    """
    parts = []
    
    if first_name:
        parts.append(first_name)
    
    if username:
        parts.append(f"(@{username})")
    
    parts.append(f"ID: {user_id}")
    
    return " ".join(parts)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Разбиение списка на чанки
    
    Args:
        lst: Исходный список
        chunk_size: Размер чанка
        
    Returns:
        Список чанков
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def is_admin_user(user_id: int) -> bool:
    """
    Проверка, является ли пользователь администратором
    
    Args:
        user_id: ID пользователя
        
    Returns:
        True если администратор, False если нет
    """
    from config.settings import ADMIN_IDS
    return user_id in ADMIN_IDS


def get_russian_plural(number: int, forms: tuple) -> str:
    """
    Получение правильной формы множественного числа для русского языка
    
    Args:
        number: Число
        forms: Кортеж с формами (1, 2-4, 5-0)
        
    Returns:
        Правильная форма
    """
    if number % 10 == 1 and number % 100 != 11:
        return forms[0]
    elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
        return forms[1]
    else:
        return forms[2]


def format_subscription_info(end_date: datetime, is_active: bool) -> str:
    """
    Форматирование информации о подписке
    
    Args:
        end_date: Дата окончания подписки
        is_active: Активна ли подписка
        
    Returns:
        Отформатированная строка
    """
    if not end_date:
        return "❌ Подписка отсутствует"
    
    if not is_active:
        return f"❌ Подписка истекла {format_datetime(end_date, 'short')}"
    
    time_left = get_time_until_expiry(end_date)
    return f"✅ Активна до {format_datetime(end_date, 'short')} ({time_left})"