#!/bin/bash

# Скрипт быстрой настройки Payment Bot
set -e

echo "🚀 Настройка Telegram Payment Bot..."

# Переходим в директорию проекта
cd "$(dirname "$0")"

# Проверка Python версии
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Python 3 не найден"
    exit 1
fi

python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python версия: $python_version"

# Удаление старого виртуального окружения
if [ -d "venv" ]; then
    echo "🗑️ Удаление старого виртуального окружения..."
    rm -rf venv
fi

# Создание виртуального окружения
echo "📦 Создание виртуального окружения..."
$PYTHON_CMD -m venv venv

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
echo "⬆️ Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo "📚 Установка зависимостей..."
pip install -r requirements.txt

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data logs backups

# Проверка установки
echo "🧪 Проверка установки..."
python -c "
try:
    from aiogram.fsm.storage.memory import MemoryStorage
    from config.settings import TELEGRAM_BOT_TOKEN
    print('✅ Все модули успешно импортированы')
    if TELEGRAM_BOT_TOKEN:
        print('✅ Токен бота найден')
    else:
        print('⚠️ Токен бота не настроен в .env')
except Exception as e:
    print(f'❌ Ошибка: {e}')
    exit(1)
"

# Инициализация базы данных
echo "🗄️ Инициализация базы данных..."
python -c "
import asyncio
import sys
sys.path.append('.')
try:
    from database.database import init_database
    asyncio.run(init_database())
    print('✅ База данных инициализирована')
except Exception as e:
    print(f'❌ Ошибка инициализации БД: {e}')
    exit(1)
"

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте настройки в .env файле"
echo "2. Запустите бота: ./start.sh"
echo ""
echo "📞 Поддержка:"
echo "• Убедитесь, что бот добавлен в канал как администратор"
echo "• Настройте ЮKassa для приема платежей"
echo ""

# Создание скрипта запуска
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Запуск Payment Bot..."
python main.py
EOF

chmod +x start.sh

echo "✅ Создан скрипт запуска: ./start.sh"