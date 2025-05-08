"""
Модуль для интеграции с n8n и ИИ для интерпретации нумерологических расчетов.
Предоставляет функции для отправки данных расчетов на интерпретацию и получения результатов.
"""

import aiohttp
import json
import logging
from typing import Dict, Any, Optional, Union

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL для интеграции с n8n
N8N_BASE_URL = "http://n8n:5678"  # Или другой адрес, если n8n развернут отдельно
MINI_REPORT_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-mini-report"
FULL_REPORT_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-full-report"
COMPATIBILITY_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-compatibility"
WEEKLY_FORECAST_WEBHOOK = f"{N8N_BASE_URL}/webhook/weekly-forecast"

# Таймаут для запросов (в секундах)
REQUEST_TIMEOUT = 60


async def send_to_n8n(webhook_url: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Отправляет данные на webhook n8n и возвращает ответ.
    
    Args:
        webhook_url: URL вебхука n8n
        data: Словарь с данными для отправки
        
    Returns:
        Ответ от n8n в виде словаря или None в случае ошибки
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=data,
                timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error from n8n webhook: {response.status}, {await response.text()}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"Connection error to n8n: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending data to n8n: {e}")
        return None


async def get_mini_report_interpretation(numerology_data: Dict[str, Any]) -> Optional[str]:
    """
    Получает интерпретацию мини-отчета от ИИ через n8n.
    
    Args:
        numerology_data: Словарь с нумерологическими расчетами
        
    Returns:
        Строка с интерпретацией или None в случае ошибки
    """
    response = await send_to_n8n(MINI_REPORT_WEBHOOK, numerology_data)
    if response and "interpretation" in response:
        return response["interpretation"]
    return None


async def get_full_report_interpretation(numerology_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Получает полную интерпретацию для PDF-отчета от ИИ через n8n.
    
    Args:
        numerology_data: Словарь с нумерологическими расчетами
        
    Returns:
        Словарь с разделами интерпретации или None в случае ошибки
    """
    response = await send_to_n8n(FULL_REPORT_WEBHOOK, numerology_data)
    if response and "full_interpretation" in response:
        return response["full_interpretation"]
    return None


async def get_compatibility_interpretation(compatibility_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Получает интерпретацию совместимости от ИИ через n8n.
    
    Args:
        compatibility_data: Словарь с расчетами совместимости
        
    Returns:
        Словарь с интерпретацией совместимости или None в случае ошибки
    """
    response = await send_to_n8n(COMPATIBILITY_WEBHOOK, compatibility_data)
    if response and "compatibility" in response:
        return response["compatibility"]
    return None


async def get_weekly_forecast(user_data: Dict[str, Any]) -> Optional[str]:
    """
    Получает еженедельный прогноз для пользователя от ИИ через n8n.
    
    Args:
        user_data: Словарь с данными пользователя и нумерологическими показателями
        
    Returns:
        Строка с еженедельным прогнозом или None в случае ошибки
    """
    response = await send_to_n8n(WEEKLY_FORECAST_WEBHOOK, user_data)
    if response and "forecast" in response:
        return response["forecast"]
    return None