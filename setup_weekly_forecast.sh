#!/bin/bash
# Скрипт для настройки и запуска еженедельных прогнозов через cron

# Путь к директории проекта
PROJECT_DIR="$(dirname "$(readlink -f "$0")")"
PYTHON_PATH="$(which python3)"

# Создание cron-задачи для запуска еженедельных прогнозов каждый понедельник в 8:00
CRON_JOB="0 8 * * 1 cd $PROJECT_DIR && $PYTHON_PATH $PROJECT_DIR/weekly_forecast.py >> $PROJECT_DIR/weekly_forecast.log 2>&1"

# Проверка наличия текущих cron-задач
CURRENT_CRONTAB=$(crontab -l 2>/dev/null || echo "")

# Проверка, существует ли уже такая задача
if [[ $CURRENT_CRONTAB == *"weekly_forecast.py"* ]]; then
    echo "Cron-задача для еженедельных прогнозов уже существует"
else
    # Добавление новой задачи в crontab
    (echo "$CURRENT_CRONTAB"; echo "$CRON_JOB") | crontab -
    echo "Cron-задача для еженедельных прогнозов успешно добавлена"
fi

echo "Настройка еженедельных прогнозов завершена"
