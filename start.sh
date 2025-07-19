#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Запуск Payment Bot..."
python main.py
