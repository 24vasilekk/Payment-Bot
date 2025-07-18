#!/bin/bash

# Скрипт резервного копирования Payment Bot
# Создает бэкапы базы данных, конфигурации и логов

set -e

# Конфигурация
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BOT_DIR}/backups"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="payment_bot_backup_${DATE}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Начинаем резервное копирование Payment Bot...${NC}"

# Создаем директорию для бэкапов
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_PATH}"

echo -e "${YELLOW}📁 Директория бэкапа: ${BACKUP_PATH}${NC}"

# 1. Бэкап базы данных
echo -e "${YELLOW}🗄️ Создание бэкапа базы данных...${NC}"
if [ -f "${BOT_DIR}/data/users.db" ]; then
    cp "${BOT_DIR}/data/users.db" "${BACKUP_PATH}/users.db"
    echo -e "${GREEN}✅ База данных скопирована${NC}"
else
    echo -e "${RED}❌ База данных не найдена${NC}"
fi

# 2. Бэкап конфигурации (без секретных данных)
echo -e "${YELLOW}⚙️ Создание бэкапа конфигурации...${NC}"
if [ -f "${BOT_DIR}/.env.example" ]; then
    cp "${BOT_DIR}/.env.example" "${BACKUP_PATH}/.env.example"
    echo -e "${GREEN}✅ Пример конфигурации скопирован${NC}"
fi

# Создаем резервную копию структуры проекта
echo -e "${YELLOW}📋 Создание списка файлов проекта...${NC}"
find "${BOT_DIR}" -type f -name "*.py" > "${BACKUP_PATH}/project_files.txt"
find "${BOT_DIR}" -type f -name "*.txt" >> "${BACKUP_PATH}/project_files.txt"
find "${BOT_DIR}" -type f -name "*.md" >> "${BACKUP_PATH}/project_files.txt"
find "${BOT_DIR}" -type f -name "*.yml" >> "${BACKUP_PATH}/project_files.txt"
find "${BOT_DIR}" -type f -name "*.yaml" >> "${BACKUP_PATH}/project_files.txt"
find "${BOT_DIR}" -type f -name "Dockerfile*" >> "${BACKUP_PATH}/project_files.txt"
echo -e "${GREEN}✅ Список файлов создан${NC}"

# 3. Бэкап важных логов (последние 100 строк)
echo -e "${YELLOW}📝 Создание бэкапа логов...${NC}"
if [ -d "${BOT_DIR}/logs" ]; then
    mkdir -p "${BACKUP_PATH}/logs"
    
    for log_file in "${BOT_DIR}/logs"/*.log; do
        if [ -f "$log_file" ]; then
            filename=$(basename "$log_file")
            tail -n 100 "$log_file" > "${BACKUP_PATH}/logs/${filename}.tail"
        fi
    done
    echo -e "${GREEN}✅ Логи скопированы${NC}"
else
    echo -e "${YELLOW}⚠️ Директория логов не найдена${NC}"
fi

# 4. Создание метаданных бэкапа
echo -e "${YELLOW}📊 Создание метаданных...${NC}"
cat > "${BACKUP_PATH}/backup_info.txt" << EOF
Payment Bot Backup Information
==============================

Backup Date: $(date)
Backup Name: ${BACKUP_NAME}
Bot Directory: ${BOT_DIR}
Backup Size: $(du -sh "${BACKUP_PATH}" | cut -f1)

Database Info:
$(if [ -f "${BOT_DIR}/data/users.db" ]; then 
    echo "- Database file exists"
    echo "- Size: $(ls -lh "${BOT_DIR}/data/users.db" | awk '{print $5}')"
    echo "- Modified: $(ls -l "${BOT_DIR}/data/users.db" | awk '{print $6, $7, $8}')"
else 
    echo "- Database file not found"
fi)

System Info:
- OS: $(uname -s)
- Python Version: $(python3 --version 2>/dev/null || echo "Not found")
- Disk Space: $(df -h "${BOT_DIR}" | tail -1 | awk '{print "Used: " $3 ", Available: " $4}')

Files in backup:
$(find "${BACKUP_PATH}" -type f | wc -l) files
$(du -sh "${BACKUP_PATH}" | cut -f1) total size
EOF

echo -e "${GREEN}✅ Метаданные созданы${NC}"

# 5. Сжатие бэкапа (опционально)
if command -v tar &> /dev/null; then
    echo -e "${YELLOW}🗜️ Сжатие бэкапа...${NC}"
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    
    if [ $? -eq 0 ]; then
        rm -rf "${BACKUP_PATH}"
        echo -e "${GREEN}✅ Бэкап сжат: ${BACKUP_NAME}.tar.gz${NC}"
        FINAL_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    else
        echo -e "${RED}❌ Ошибка сжатия, оставляем несжатый бэкап${NC}"
        FINAL_BACKUP="${BACKUP_PATH}"
    fi
else
    echo -e "${YELLOW}⚠️ tar не найден, пропускаем сжатие${NC}"
    FINAL_BACKUP="${BACKUP_PATH}"
fi

# 6. Очистка старых бэкапов (оставляем последние 7)
echo -e "${YELLOW}🧹 Очистка старых бэкапов...${NC}"
cd "${BACKUP_DIR}"

# Считаем количество бэкапов
backup_count=$(ls -1 payment_bot_backup_* 2>/dev/null | wc -l)

if [ $backup_count -gt 7 ]; then
    # Удаляем самые старые, оставляем 7 последних
    ls -1t payment_bot_backup_* | tail -n +8 | xargs rm -rf
    removed=$((backup_count - 7))
    echo -e "${GREEN}✅ Удалено старых бэкапов: ${removed}${NC}"
else
    echo -e "${GREEN}✅ Очистка не требуется (бэкапов: ${backup_count})${NC}"
fi

# 7. Проверка целостности
echo -e "${YELLOW}🔍 Проверка целостности бэкапа...${NC}"
if [ -f "${FINAL_BACKUP}" ] || [ -d "${FINAL_BACKUP}" ]; then
    backup_size=$(du -sh "${FINAL_BACKUP}" | cut -f1)
    echo -e "${GREEN}✅ Бэкап создан успешно${NC}"
    echo -e "${GREEN}📦 Размер: ${backup_size}${NC}"
    echo -e "${GREEN}📍 Путь: ${FINAL_BACKUP}${NC}"
else
    echo -e "${RED}❌ Ошибка создания бэкапа${NC}"
    exit 1
fi

# 8. Отправка уведомления (если настроено)
if [ ! -z "${BACKUP_NOTIFICATION_URL}" ]; then
    echo -e "${YELLOW}📡 Отправка уведомления...${NC}"
    curl -s -X POST "${BACKUP_NOTIFICATION_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"✅ Payment Bot backup completed: ${BACKUP_NAME}\"}" \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Уведомление отправлено${NC}"
    else
        echo -e "${YELLOW}⚠️ Не удалось отправить уведомление${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Резервное копирование завершено успешно!${NC}"
echo -e "${GREEN}📦 Бэкап: ${FINAL_BACKUP}${NC}"
echo -e "${GREEN}📊 Размер: $(du -sh "${FINAL_BACKUP}" | cut -f1)${NC}"
echo ""

# Вывод инструкций по восстановлению
echo -e "${YELLOW}📖 Инструкции по восстановлению:${NC}"
echo -e "${YELLOW}1. Остановите бота${NC}"
echo -e "${YELLOW}2. Распакуйте бэкап: tar -xzf ${BACKUP_NAME}.tar.gz${NC}"
echo -e "${YELLOW}3. Скопируйте users.db в директорию data/${NC}"
echo -e "${YELLOW}4. Восстановите конфигурацию${NC}"
echo -e "${YELLOW}5. Запустите бота${NC}"