#!/bin/bash

# Скрипт развертывания Payment Bot
# Автоматизирует процесс деплоя на сервер

set -e

# Конфигурация
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="payment-bot"
PYTHON_VERSION="3.9"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода заголовков
print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Функция проверки команды
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ Команда $1 не найдена${NC}"
        return 1
    fi
    return 0
}

print_header "🚀 РАЗВЕРТЫВАНИЕ PAYMENT BOT"

echo -e "${GREEN}📁 Директория проекта: ${BOT_DIR}${NC}"
echo -e "${GREEN}🐍 Требуемая версия Python: ${PYTHON_VERSION}+${NC}"

# 1. Проверка системных требований
print_header "🔍 ПРОВЕРКА СИСТЕМЫ"

# Проверка Python
if check_command python3; then
    python_version=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✅ Python найден: ${python_version}${NC}"
    
    # Проверка версии
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
        echo -e "${GREEN}✅ Версия Python подходит${NC}"
    else
        echo -e "${RED}❌ Требуется Python ${PYTHON_VERSION} или выше${NC}"
        echo -e "${YELLOW}💡 Установите актуальную версию Python${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Python не найден${NC}"
    exit 1
fi

# Проверка pip
if check_command pip3; then
    echo -e "${GREEN}✅ pip найден${NC}"
else
    echo -e "${RED}❌ pip не найден${NC}"
    exit 1
fi

# Проверка git (опционально)
if check_command git; then
    echo -e "${GREEN}✅ git найден${NC}"
    
    # Показываем информацию о репозитории
    if [ -d "${BOT_DIR}/.git" ]; then
        branch=$(git -C "${BOT_DIR}" branch --show-current 2>/dev/null || echo "unknown")
        commit=$(git -C "${BOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")
        echo -e "${GREEN}📊 Ветка: ${branch}, коммит: ${commit}${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ git не найден (не критично)${NC}"
fi

# 2. Подготовка окружения
print_header "📦 ПОДГОТОВКА ОКРУЖЕНИЯ"

cd "${BOT_DIR}"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🔨 Создание виртуального окружения...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Виртуальное окружение создано${NC}"
else
    echo -e "${GREEN}✅ Виртуальное окружение найдено${NC}"
fi

# Активация виртуального окружения
echo -e "${YELLOW}🔧 Активация виртуального окружения...${NC}"
source venv/bin/activate

# Обновление pip
echo -e "${YELLOW}⬆️ Обновление pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1

# Установка зависимостей
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📚 Установка зависимостей...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Зависимости установлены${NC}"
else
    echo -e "${RED}❌ Файл requirements.txt не найден${NC}"
    exit 1
fi

# 3. Проверка конфигурации
print_header "⚙️ ПРОВЕРКА КОНФИГУРАЦИИ"

# Проверка .env файла
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ Файл .env найден${NC}"
    
    # Проверка обязательных переменных
    required_vars=("TELEGRAM_BOT_TOKEN" "YOOKASSA_SHOP_ID" "YOOKASSA_SECRET_KEY" "CHANNEL_ID")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env || grep -q "^${var}=YOUR_" .env; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${RED}❌ Не настроены обязательные переменные:${NC}"
        printf '%s\n' "${missing_vars[@]}" | sed 's/^/   - /'
        echo -e "${YELLOW}💡 Отредактируйте .env файл перед продолжением${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ Все обязательные переменные настроены${NC}"
    fi
else
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠️ Файл .env не найден, создаем из примера...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}📝 Отредактируйте .env файл и запустите деплой снова${NC}"
        exit 1
    else
        echo -e "${RED}❌ Файлы .env и .env.example не найдены${NC}"
        exit 1
    fi
fi

# 4. Создание директорий
print_header "📁 СОЗДАНИЕ ДИРЕКТОРИЙ"

directories=("data" "logs" "backups")
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✅ Создана директория: $dir${NC}"
    else
        echo -e "${GREEN}✅ Директория существует: $dir${NC}"
    fi
done

# Установка прав доступа
chmod 755 data logs backups
echo -e "${GREEN}✅ Права доступа установлены${NC}"

# 5. Инициализация базы данных
print_header "🗄️ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ"

echo -e "${YELLOW}🔧 Инициализация базы данных...${NC}"
python3 -c "
import asyncio
import sys
sys.path.append('.')
try:
    from database.database import init_database
    asyncio.run(init_database())
    print('✅ База данных инициализирована')
except Exception as e:
    print(f'❌ Ошибка инициализации БД: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ База данных готова${NC}"
else
    echo -e "${RED}❌ Ошибка инициализации базы данных${NC}"
    exit 1
fi

# 6. Создание systemd сервиса (для Linux)
print_header "🔧 НАСТРОЙКА СЕРВИСА"

if command -v systemctl &> /dev/null; then
    echo -e "${YELLOW}🔧 Создание systemd сервиса...${NC}"
    
    # Создаем файл сервиса
    cat > "${SERVICE_NAME}.service" << EOF
[Unit]
Description=Telegram Payment Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=${BOT_DIR}
ExecStart=${BOT_DIR}/venv/bin/python ${BOT_DIR}/main.py
Restart=always
RestartSec=10
Environment=PATH=${BOT_DIR}/venv/bin

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}✅ Файл сервиса создан: ${SERVICE_NAME}.service${NC}"
    echo -e "${YELLOW}💡 Для установки сервиса выполните:${NC}"
    echo -e "${YELLOW}   sudo cp ${SERVICE_NAME}.service /etc/systemd/system/${NC}"
    echo -e "${YELLOW}   sudo systemctl daemon-reload${NC}"
    echo -e "${YELLOW}   sudo systemctl enable ${SERVICE_NAME}${NC}"
    
else
    echo -e "${YELLOW}⚠️ systemctl не найден, пропускаем создание сервиса${NC}"
fi

# 7. Создание скриптов управления
print_header "📜 СОЗДАНИЕ СКРИПТОВ"

# Скрипт запуска
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Запуск Payment Bot..."
python main.py
EOF

chmod +x start.sh
echo -e "${GREEN}✅ Создан скрипт запуска: start.sh${NC}"

# Скрипт остановки
cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Остановка Payment Bot..."
pkill -f "python main.py"
sleep 2
if pgrep -f "python main.py" > /dev/null; then
    echo "⚠️ Принудительная остановка..."
    pkill -9 -f "python main.py"
fi
echo "✅ Bot остановлен"
EOF

chmod +x stop.sh
echo -e "${GREEN}✅ Создан скрипт остановки: stop.sh${NC}"

# Скрипт статуса
cat > status.sh << 'EOF'
#!/bin/bash
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Payment Bot запущен"
    echo "PID: $(pgrep -f 'python main.py')"
    echo "Время работы: $(ps -o etime= -p $(pgrep -f 'python main.py') | tr -d ' ')"
else
    echo "❌ Payment Bot не запущен"
fi
EOF

chmod +x status.sh
echo -e "${GREEN}✅ Создан скрипт статуса: status.sh${NC}"

# Делаем скрипты исполняемыми
chmod +x scripts/*.sh
echo -e "${GREEN}✅ Права на скрипты установлены${NC}"

# 8. Проверка конфигурации
print_header "🧪 ТЕСТИРОВАНИЕ КОНФИГУРАЦИИ"

echo -e "${YELLOW}🧪 Проверка импортов...${NC}"
python3 -c "
import sys
sys.path.append('.')
try:
    from config.settings import TELEGRAM_BOT_TOKEN, YOOKASSA_SHOP_ID
    from database.database import db
    from services.yookassa_service import yookassa_service
    print('✅ Все модули импортируются корректно')
except Exception as e:
    print(f'❌ Ошибка импорта: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибки в конфигурации${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Конфигурация корректна${NC}"

# 9. Финальная информация
print_header "🎉 РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО"

echo -e "${GREEN}✅ Payment Bot успешно развернут!${NC}"
echo ""
echo -e "${YELLOW}📋 Следующие шаги:${NC}"
echo -e "${YELLOW}1. Проверьте настройки в .env файле${NC}"
echo -e "${YELLOW}2. Запустите бота: ./start.sh${NC}"
echo -e "${YELLOW}3. Проверьте статус: ./status.sh${NC}"
echo ""
echo -e "${YELLOW}📚 Полезные команды:${NC}"
echo -e "${YELLOW}   ./start.sh    - запуск бота${NC}"
echo -e "${YELLOW}   ./stop.sh     - остановка бота${NC}"
echo -e "${YELLOW}   ./status.sh   - проверка статуса${NC}"
echo -e "${YELLOW}   tail -f logs/bot.log - просмотр логов${NC}"
echo ""
echo -e "${YELLOW}🔗 Важные файлы:${NC}"
echo -e "${YELLOW}   📄 Конфигурация: .env${NC}"
echo -e "${YELLOW}   🗄️ База данных: data/users.db${NC}"
echo -e "${YELLOW}   📝 Логи: logs/bot.log${NC}"
echo ""
echo -e "${YELLOW}🚨 Не забудьте:${NC}"
echo -e "${YELLOW}   • Настроить webhook URL в ЮKassa${NC}"
echo -e "${YELLOW}   • Добавить бота в канал как администратора${NC}"
echo -e "${YELLOW}   • Проверить работу платежей${NC}"
echo ""
echo -e "${GREEN}🎊 Удачного использования!${NC}"