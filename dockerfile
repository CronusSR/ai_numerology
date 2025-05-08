FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей для weasyprint
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для PDF-отчетов
RUN mkdir -p /app/pdfs && chmod 777 /app/pdfs

# Установка timezone
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Запуск приложения (определяется в docker-compose.yml)
CMD ["python", "bot.py"]