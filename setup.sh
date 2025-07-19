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

# Установка зависимостей с обработкой ошибок
echo "📚 Установка зависимостей..."
if pip install -r requirements.txt; then
    echo "✅ Зависимости установлены успешно"
else
    echo "⚠️ Ошибка установки зависимостей, пробуем установить вручную..."
    
    # Устанавливаем по одной
    pip install aiogram==3.4.1
    pip install aiohttp==3.9.1 
    pip install python-dotenv==1.0.0
    pip install aiosqlite==0.19.0
    pip install apscheduler==3.10.4
    pip install python-dateutil==2.8.2
    pip install PyJWT==2.8.0
    pip install "cryptography>=41.0.0"
    pip install aiohttp-cors==0.7.0
    
    echo "✅ Зависимости установлены вручную"
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data logs backups

# Проверка установки
echo "🧪 Проверка установки..."
python -c "
try:
    from aiogram.fsm.storage.memory import MemoryStorage
    print('✅ aiogram импортирован успешно')
    
    from config.settings import TELEGRAM_BOT_TOKEN
    print('✅ Конфигурация загружена')
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != 'YOUR_BOT_TOKEN':
        print('✅ Токен бота настроен')
    else:
        print('⚠️ Токен бота не настроен в .env')
        
except ImportError as e:
    print(f'❌ Ошибка импорта: {e}')
    exit(1)
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
    # Не выходим из скрипта, продолжаем
"

# Создание скрипта запуска
echo "📝 Создание скрипта запуска..."
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Запуск Payment Bot..."
python main.py
EOF

chmod +x start.sh

# Создание скрипта остановки
cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Остановка Payment Bot..."
pkill -f "python main.py"
echo "✅ Bot остановлен"
EOF

chmod +x stop.sh

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте настройки в .env файле"
echo "2. Убедитесь, что бот добавлен в канал как администратор"
echo "3. Запустите бота: ./start.sh"
echo ""
echo "📚 Полезные команды:"
echo "   ./start.sh  - запуск бота"
echo "   ./stop.sh   - остановка бота"
echo ""
echo "📞 Поддержка:"
echo "• Логи сохраняются в logs/bot.log"
echo "• Настройте ЮKassa для приема платежей"
echo ""