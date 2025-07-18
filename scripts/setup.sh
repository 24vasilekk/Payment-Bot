#!/bin/bash

# Скрипт первоначальной настройки Payment Bot
set -e

echo "🚀 Настройка Telegram Payment Bot..."

# Проверка Python версии
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [[ $(echo "$python_version >= $required_version" | bc -l) -eq 0 ]]; then
    echo "❌ Требуется Python $required_version или выше. Установлена версия: $python_version"
    exit 1
fi

echo "✅ Python версия: $python_version"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

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
mkdir -p data logs scripts

# Копирование примера .env файла
if [ ! -f ".env" ]; then
    echo "⚙️ Создание .env файла..."
    cp .env.example .env
    echo "📝 Отредактируйте .env файл своими данными!"
else
    echo "✅ .env файл уже существует"
fi

# Проверка наличия основных переменных в .env
echo "🔍 Проверка конфигурации..."
source .env 2>/dev/null || echo "⚠️ Не удалось загрузить .env файл"

required_vars=("TELEGRAM_BOT_TOKEN" "YOOKASSA_SHOP_ID" "YOOKASSA_SECRET_KEY" "CHANNEL_ID")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ Отсутствуют обязательные переменные в .env:"
    printf '   - %s\n' "${missing_vars[@]}"
    echo ""
    echo "📝 Пожалуйста, заполните эти переменные в .env файле"
    exit 1
fi

# Инициализация базы данных
echo "🗄️ Инициализация базы данных..."
python3 -c "
import asyncio
import sys
sys.path.append('.')
from database.database import init_database
asyncio.run(init_database())
print('✅ База данных инициализирована')
"

# Создание systemd сервиса (для Linux)
if [ -f "/etc/systemd/system/" ] && command -v systemctl &> /dev/null; then
    echo "🔧 Создание systemd сервиса..."
    
    cat > payment-bot.service << EOF
[Unit]
Description=Telegram Payment Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PATH=$(pwd)/venv/bin

[Install]
WantedBy=multi-user.target
EOF

    echo "📋 Сервис создан: payment-bot.service"
    echo "   Для установки выполните:"
    echo "   sudo cp payment-bot.service /etc/systemd/system/"
    echo "   sudo systemctl daemon-reload"
    echo "   sudo systemctl enable payment-bot"
    echo "   sudo systemctl start payment-bot"
fi

# Создание скрипта запуска
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
EOF

chmod +x start.sh

# Создание скрипта остановки
cat > stop.sh << 'EOF'
#!/bin/bash
pkill -f "python main.py"
echo "Bot stopped"
EOF

chmod +x stop.sh

# Создание скрипта для проверки статуса
cat > status.sh << 'EOF'
#!/bin/bash
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Bot is running"
    echo "PID: $(pgrep -f 'python main.py')"
else
    echo "❌ Bot is not running"
fi
EOF

chmod +x status.sh

echo ""
echo "🎉 Настройка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте .env файл с вашими данными"
echo "2. Запустите бота: ./start.sh"
echo "3. Или используйте: python main.py"
echo ""
echo "📚 Дополнительные команды:"
echo "   ./start.sh   - запуск бота"
echo "   ./stop.sh    - остановка бота"
echo "   ./status.sh  - проверка статуса"
echo ""
echo "📝 Логи будут сохраняться в директории: logs/"
echo "🗄️ База данных: data/users.db"
echo ""
echo "🔗 Не забудьте настроить webhook в панели ЮKassa!"
echo "   URL: https://ваш-домен.com/webhook/yookassa"