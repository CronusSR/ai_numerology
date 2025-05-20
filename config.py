# config.py - центральный модуль конфигурации
import os
import logging
from dotenv import load_dotenv

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из файла .env
try:
    load_dotenv()
    logger.info("Переменные окружения загружены из .env")
except Exception as e:
    logger.warning(f"Ошибка при загрузке .env: {e}")
    logger.info("Используются переменные окружения системы")

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "./pdfs")

# Настройки n8n
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")
USE_EXTERNAL_WEBHOOK = os.getenv("USE_EXTERNAL_WEBHOOK", "true").lower() == "true"
EXPECT_TEXT_RESPONSE = os.getenv("EXPECT_TEXT_RESPONSE", "true").lower() == "true"

# Режим работы
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

# Директории для хранения данных и логов
CALCULATIONS_DIR = os.getenv("CALCULATIONS_DIR", "./calculations")
N8N_LOGS_DIR = os.getenv("N8N_LOGS_DIR", "./n8n_logs")

# Вывод информации о режиме работы
logger.info(f"Режим работы: {'тестовый' if TEST_MODE else 'рабочий'}")
logger.info(f"Внешний вебхук: {EXTERNAL_WEBHOOK_URL if USE_EXTERNAL_WEBHOOK else 'не используется'}")
logger.info(f"База n8n: {N8N_BASE_URL}")

# Функция для перезагрузки конфигурации
def reload_config():
    """
    Перезагружает конфигурацию из .env файла.
    Эту функцию можно вызывать при необходимости обновить настройки без перезапуска приложения.
    """
    global TEST_MODE, USE_EXTERNAL_WEBHOOK, EXTERNAL_WEBHOOK_URL, N8N_BASE_URL, EXPECT_TEXT_RESPONSE
    
    try:
        load_dotenv(override=True)  # Параметр override=True позволяет перезаписать существующие переменные
        
        # Обновляем значения
        TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
        USE_EXTERNAL_WEBHOOK = os.getenv("USE_EXTERNAL_WEBHOOK", "true").lower() == "true"
        EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")
        N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        EXPECT_TEXT_RESPONSE = os.getenv("EXPECT_TEXT_RESPONSE", "true").lower() == "true"
        
        logger.info("Конфигурация успешно перезагружена")
        logger.info(f"Режим работы: {'тестовый' if TEST_MODE else 'рабочий'}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при перезагрузке конфигурации: {e}")
        return False