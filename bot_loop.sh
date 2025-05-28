#!/bin/bash

# Переходим в директорию бота
cd ~/testing/english_learning_bot

# Активируем виртуальное окружение
source ~/testing/myenv/bin/activate

# Бесконечный цикл с автоперезапуском
while true; do
    echo "$(date): Запуск бота..."
    python3.11 bot.py
    echo "$(date): Бот остановлен. Перезапуск через 5 секунд..."
    sleep 5
done
