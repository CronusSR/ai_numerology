#!/bin/bash

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo "Файл .env не найден. Создаем на основе шаблона..."
    
    # Запрашиваем токен бота
    echo -n "Введите токен бота (BOT_TOKEN): "
    read bot_token
    
    # Создаем файл .env с минимальными настройками для тестового режима
    cat > .env << EOF
# Telegram Bot
BOT_TOKEN=${bot_token}

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=numerology_bot

# Тестовый режим
TEST_MODE=true
EOF
    
    echo "Файл .env создан с настройками для тестового режима"
fi

# Проверяем наличие директории для PDF-отчетов
if [ ! -d "pdfs" ]; then
    echo "Создаем директорию для PDF-отчетов..."
    mkdir -p pdfs
    chmod 777 pdfs
fi

# Поднимаем контейнеры
echo "Запускаем контейнеры..."
docker-compose up -d

# Вывод статуса
echo "Статус контейнеров:"
docker-compose ps

echo -e "\nДля просмотра логов используйте: docker-compose logs -f bot"
echo "Для остановки используйте: ./stop.sh или docker-compose down"