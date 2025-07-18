# 🤖 Telegram Payment Bot

Telegram бот для автоматизации платных подписок на каналы с интеграцией ЮKassa.

## ✨ Возможности

- 💳 **Прием платежей** через ЮKassa
- 🔐 **Автоматическое управление доступом** к Telegram каналу
- 📊 **Отслеживание подписок** и их продление
- 🚫 **Автоматическое исключение** неплательщиков
- 📝 **Подробное логирование** всех операций
- 🔄 **Webhook обработка** для мгновенной реакции на платежи
- 📱 **Простой интерфейс** для пользователей

## 🏗️ Архитектура

```
payment_bot/
├── main.py                     # Точка входа
├── config/
│   └── settings.py             # Настройки
├── database/
│   ├── models.py               # Модели данных
│   └── database.py             # Работа с БД
├── bot/
│   └── handlers/               # Обработчики команд
├── services/                   # Бизнес-логика
├── webhook/                    # Webhook сервер
├── tasks/                      # Фоновые задачи
└── utils/                      # Утилиты
```

## 🚀 Быстрый старт

### 1. Клонирование и установка

```bash
git clone <repository-url>
cd payment_bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env файл своими данными
```

### 3. Получение токенов и настройка

#### Telegram Bot:
1. Напишите @BotFather в Telegram
2. Создайте нового бота: `/newbot`
3. Скопируйте токен в `.env`

#### ЮKassa:
1. Зарегистрируйтесь на [yookassa.ru](https://yookassa.ru)
2. Получите Shop ID и Secret Key
3. Добавьте данные в `.env`

#### Telegram канал:
1. Создайте приватный канал
2. Добавьте бота как администратора
3. Укажите @username канала в `.env`

### 4. Запуск

```bash
python main.py
```

## 📋 Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | `1234567890:ABC...` |
| `CHANNEL_ID` | ID/username канала | `@my_channel` |
| `YOOKASSA_SHOP_ID` | ID магазина ЮKassa | `123456` |
| `YOOKASSA_SECRET_KEY` | Секретный ключ ЮKassa | `live_abc...` |
| `SUBSCRIPTION_PRICE` | Цена подписки (руб) | `500.00` |
| `WEBHOOK_HOST` | Домен для webhook'ов | `bot.example.com` |

## 🔧 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и информация |
| `/pay` | Оплата подписки |
| `/status` | Проверка статуса подписки |
| `/help` | Справка |

### Админские команды:
| Команда | Описание |
|---------|----------|
| `/admin` | Админ панель |
| `/stats` | Статистика |
| `/users` | Список пользователей |
| `/broadcast` | Рассылка сообщений |

## 📊 Мониторинг

### Логи
- `logs/bot.log` - основные логи бота
- `logs/webhook.log` - логи webhook'ов
- `logs/payments.log` - логи платежей
- `logs/errors.log` - ошибки

### База данных
- SQLite файл: `data/users.db`
- Автоматические бэкапы каждые 24 часа

## 🐳 Docker развертывание

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

## 🔐 Безопасность

### Webhook подписи
В продакшене обязательно включите проверку подписей:

```python
# webhook/handlers.py
if not verify_signature(body, signature):
    return web.Response(status=400)
```

### SSL сертификаты
Используйте HTTPS для webhook URL:
```bash
# Получение Let's Encrypt сертификата
certbot --nginx -d your-domain.com
```

## 📈 Масштабирование

### Для большой нагрузки:
1. **PostgreSQL** вместо SQLite
2. **Redis** для кэширования
3. **Celery** для фоновых задач
4. **Nginx** как reverse proxy

### Пример docker-compose для продакшена:
```yaml
services:
  bot:
    build: .
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:14
    
  redis:
    image: redis:7
    
  nginx:
    image: nginx
```

## 🛠️ Разработка

### Структура веток:
- `main` - продакшен
- `develop` - разработка
- `feature/*` - новые функции

### Тестирование:
```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=.
```

### Линтинг:
```bash
# Проверка кода
flake8 .
black .
```

## 📝 API документация

### Webhook endpoints:
- `POST /webhook/yookassa` - основные платежи
- `POST /webhook/yookassa/recurring` - регулярные платежи
- `GET /health` - проверка работоспособности

### ЮKassa интеграция:
- Создание платежа
- Проверка статуса
- Обработка webhook'ов
- Возвраты (если нужно)

## 🐛 Устранение неполадок

### Бот не отвечает:
1. Проверьте токен в `.env`
2. Убедитесь что бот запущен
3. Проверьте логи: `logs/bot.log`

### Платежи не проходят:
1. Проверьте настройки ЮKassa
2. Убедитесь что webhook доступен
3. Проверьте логи: `logs/payments.log`

### Пользователей не кикает:
1. Проверьте права бота в канале
2. Убедитесь что планировщик работает
3. Проверьте время на сервере

## 📞 Поддержка

- 📧 Email: support@example.com
- 💬 Telegram: @your_support_bot
- 🐛 Issues: GitHub Issues

## 📄 Лицензия

MIT License - см. файл `LICENSE`

## 🤝 Вклад в проект

1. Fork проекта
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

---

**⚠️ Важно:** Не забудьте настроить webhook URL в панели ЮKassa!