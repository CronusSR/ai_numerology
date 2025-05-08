# ИИ-Нумеролог - Телеграм-бот

Телеграм-бот "ИИ-Нумеролог" выполняет нумерологические расчеты, предоставляет персонализированные отчеты и прогнозы на основе искусственного интеллекта.

## Основные функции

- Сбор данных пользователя (ФИО, дата рождения)
- Выполнение нумерологических расчетов
- Предоставление бесплатного мини-отчета
- Генерация и отправка платного полного PDF-отчета
- Расчет нумерологической совместимости
- Еженедельные прогнозы для подписчиков

## Технический стек

- **Python 3.10+** - основной язык программирования
- **aiogram 3.x** - фреймворк для создания Telegram ботов
- **PostgreSQL** - база данных для хранения информации о пользователях и заказах
- **n8n** - для интеграции с API искусственного интеллекта
- **Docker** - для контейнеризации и развертывания
- **weasyprint** - для генерации PDF-отчетов

## Структура проекта

```
ИИ-Нумеролог/
├── bot.py                # Основной файл бота
├── numerology_core.py    # Модуль для нумерологических расчетов
├── database.py           # Модуль работы с базой данных
├── interpret.py          # Модуль для интеграции с n8n и ИИ
├── payment_webhook.py    # Обработчик вебхуков платежей
├── pdf_template.html     # HTML-шаблон для генерации PDF
├── requirements.txt      # Зависимости проекта
├── docker-compose.yml    # Конфигурация Docker
└── README.md             # Документация проекта
```

## Установка и запуск

### Требования

- Python 3.10 или выше
- PostgreSQL
- n8n
- Docker и docker-compose (опционально)

### Установка вручную

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/numerology-bot.git
   cd numerology-bot
   ```

2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/Mac
   # или
   venv\Scripts\activate  # Для Windows
   
   pip install -r requirements.txt
   ```

3. Создайте файл `.env` с необходимыми переменными окружения:
   ```
   # Telegram Bot
   BOT_TOKEN=your_bot_token_here
   PAYMENT_PROVIDER_TOKEN=your_payment_provider_token_here
   PAYMENT_TOKEN_SECRET=your_payment_secret_here
   
   # PostgreSQL
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=numerology_bot
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   # n8n
   N8N_BASE_URL=http://localhost:5678
   
   # Другие настройки
   ADMIN_USER_ID=your_telegram_id
   PDF_STORAGE_PATH=./pdfs
   ```

4. Создайте необходимые таблицы в базе данных:
   ```bash
   psql -U postgres -d numerology_bot -f schema.sql
   ```

5. Запустите бота:
   ```bash
   python bot.py
   ```

### Запуск с Docker

1. Убедитесь, что Docker и docker-compose установлены в вашей системе.

2. Создайте файл `.env` как описано выше.

3. Запустите контейнеры:
   ```bash
   docker-compose up -d
   ```

4. Проверьте логи:
   ```bash
   docker-compose logs -f bot
   ```

## Настройка n8n для ИИ-интеграции

1. Откройте веб-интерфейс n8n (по умолчанию http://localhost:5678).

2. Создайте следующие рабочие процессы (workflows):
   - `numerology-mini-report` - для обработки мини-отчетов
   - `numerology-full-report` - для обработки полных отчетов
   - `numerology-compatibility` - для обработки расчетов совместимости
   - `weekly-forecast` - для еженедельных прогнозов

3. Настройте для каждого процесса:
   - HTTP Webhook для получения данных от бота
   - Интеграцию с API ИИ (OpenAI, Claude и т.д.)
   - HTTP Response для возврата результатов боту

## Команды бота

- `/start` - Запуск бота и начало взаимодействия
- `/report` - Получение последнего купленного отчета
- `/subscribe` - Управление подпиской на еженедельные прогнозы
- `/compatibility` - Расчет совместимости с другим человеком
- `/help` - Справка и информация о боте
- `/settings` - Настройки языка и уведомлений

## Лицензия

Проект распространяется под лицензией MIT.

## Поддержка

По всем вопросам и предложениям обращайтесь через issues в GitHub или напрямую к администратору бота.