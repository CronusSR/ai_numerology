#!/usr/bin/env python
# toggle_test_mode.py - скрипт для переключения тестового режима

import os
import sys
import logging
from dotenv import load_dotenv, set_key

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def toggle_test_mode():
    """
    Переключает режим TEST_MODE в файле .env
    """
    # Загружаем текущие переменные окружения
    load_dotenv()
    
    # Получаем текущее значение TEST_MODE
    current_mode = os.getenv("TEST_MODE", "true").lower()
    
    # Определяем новое значение
    new_mode = "false" if current_mode == "true" else "true"
    
    # Обновляем значение в файле .env
    try:
        set_key(".env", "TEST_MODE", new_mode)
        logger.info(f"Режим TEST_MODE изменен с '{current_mode}' на '{new_mode}'")
        logger.info(f"Бот теперь будет работать в {'тестовом' if new_mode == 'true' else 'рабочем'} режиме после перезапуска")
        
        # Если передан аргумент --reload, перезагружаем конфигурацию без перезапуска бота
        if len(sys.argv) > 1 and sys.argv[1] == "--reload":
            try:
                import config
                if config.reload_config():
                    logger.info("Конфигурация успешно перезагружена без перезапуска бота")
                else:
                    logger.warning("Не удалось перезагрузить конфигурацию")
            except ImportError:
                logger.warning("Не удалось импортировать модуль config для перезагрузки конфигурации")
        else:
            logger.info("Для применения изменений перезапустите бота или используйте --reload для горячей перезагрузки")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении .env файла: {e}")
        return False

if __name__ == "__main__":
    toggle_test_mode()