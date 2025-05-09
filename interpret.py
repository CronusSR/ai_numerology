"""
Модуль для интеграции с n8n и ИИ для интерпретации нумерологических расчетов.
Предоставляет функции для отправки данных расчетов на интерпретацию и получения результатов.
"""

import aiohttp
import json
import logging
import os
from typing import Dict, Any, Optional, Union

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL для интеграции с n8n
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://n8n:5678")  # Или другой адрес, если n8n развернут отдельно
MINI_REPORT_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-mini-report"
FULL_REPORT_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-full-report"
COMPATIBILITY_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-compatibility"
WEEKLY_FORECAST_WEBHOOK = f"{N8N_BASE_URL}/webhook/weekly-forecast"

# Таймаут для запросов (в секундах)
REQUEST_TIMEOUT = 60

# Режим тестирования (без реальных вызовов API)
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"


async def send_to_n8n(webhook_url: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Отправляет данные на webhook n8n и возвращает ответ.
    
    Args:
        webhook_url: URL вебхука n8n
        data: Словарь с данными для отправки
        
    Returns:
        Ответ от n8n в виде словаря или None в случае ошибки
    """
    # В тестовом режиме возвращаем фейковые данные
    if TEST_MODE:
        logger.info(f"TEST MODE: Имитация отправки данных на {webhook_url}")
        return generate_test_response(webhook_url, data)

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


async def send_to_n8n_for_interpretation(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Отправляет данные на интерпретацию через n8n в зависимости от типа отчета.
    
    Args:
        data: Словарь с нумерологическими расчетами
        report_type: Тип отчета ('mini', 'full', 'compatibility_mini', 'compatibility')
        
    Returns:
        Словарь с результатами интерпретации или пустой словарь в случае ошибки
    """
    try:
        if report_type == 'mini':
            result = await send_to_n8n(MINI_REPORT_WEBHOOK, data)
            if not result:
                logger.error("Failed to get mini report interpretation")
                return {"mini_report": "Извините, не удалось получить интерпретацию. Пожалуйста, попробуйте позже."}
            return result
        elif report_type == 'full':
            result = await send_to_n8n(FULL_REPORT_WEBHOOK, data)
            if not result:
                logger.error("Failed to get full report interpretation")
                return {"full_report": {"introduction": "Извините, не удалось получить интерпретацию."}}
            return result
        elif report_type == 'compatibility_mini':
            result = await send_to_n8n(COMPATIBILITY_WEBHOOK, {"type": "mini", **data})
            if not result:
                logger.error("Failed to get compatibility mini report interpretation")
                return {"compatibility_mini_report": "Извините, не удалось получить интерпретацию."}
            return result
        elif report_type == 'compatibility':
            result = await send_to_n8n(COMPATIBILITY_WEBHOOK, {"type": "full", **data})
            if not result:
                logger.error("Failed to get compatibility full report interpretation")
                return {"compatibility_report": {"introduction": "Извините, не удалось получить интерпретацию."}}
            return result
        else:
            logger.error(f"Unknown report type: {report_type}")
            return {}
    except Exception as e:
        logger.error(f"Error in send_to_n8n_for_interpretation: {e}")
        return {}


def generate_test_response(webhook_url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерирует тестовый ответ для различных типов запросов в режиме тестирования.
    
    Args:
        webhook_url: URL вебхука n8n
        data: Словарь с данными для отправки
        
    Returns:
        Тестовый ответ в зависимости от типа запроса
    """
    if "numerology-mini-report" in webhook_url:
        life_path = data.get("life_path", 1)
        expression = data.get("expression", 1)
        return {
            "interpretation": f"""
Ваш мини-отчет (тестовый режим):

Число жизненного пути: {life_path}
Вы обладаете сильным потенциалом лидера и первооткрывателя. Ваша независимость и оригинальность мышления помогают находить необычные решения стандартных задач.

Число выражения: {expression}
Вы наделены творческим мышлением и умеете вдохновлять окружающих своим энтузиазмом. Ваша коммуникабельность помогает налаживать контакты в различных сферах.

Для получения полного анализа рекомендуем заказать подробный PDF-отчет, содержащий более глубокую интерпретацию ваших нумерологических показателей и персональные рекомендации.
            """,
            "mini_report": f"""
Ваш мини-отчет (тестовый режим):

Число жизненного пути: {life_path}
Вы обладаете сильным потенциалом лидера и первооткрывателя. Ваша независимость и оригинальность мышления помогают находить необычные решения стандартных задач.

Число выражения: {expression}
Вы наделены творческим мышлением и умеете вдохновлять окружающих своим энтузиазмом. Ваша коммуникабельность помогает налаживать контакты в различных сферах.

Для получения полного анализа рекомендуем заказать подробный PDF-отчет, содержащий более глубокую интерпретацию ваших нумерологических показателей и персональные рекомендации.
            """
        }
    
    elif "numerology-full-report" in webhook_url:
        life_path = data.get("life_path", 1)
        expression = data.get("expression", 1)
        soul_urge = data.get("soul_urge", 1)
        personality = data.get("personality", 1)
        
        return {
            "full_interpretation": {
                "introduction": "Этот нумерологический отчет создан на основе ваших персональных данных и содержит глубокий анализ вашей личности, потенциала и жизненного пути.",
                "life_path_interpretation": f"Число жизненного пути {life_path} указывает на вашу независимость и лидерские качества.",
                "expression_interpretation": f"Число выражения {expression} раскрывает ваш творческий потенциал и ораторские способности.",
                "soul_interpretation": f"Число души {soul_urge} показывает ваши внутренние мотивы и стремления.",
                "personality_interpretation": f"Число личности {personality} отражает вашу внешнюю проекцию и то, как вас воспринимают окружающие.",
                "life_path_detailed": "Подробный анализ числа жизненного пути...",
                "expression_detailed": "Подробный анализ числа выражения...",
                "soul_detailed": "Подробный анализ числа души...",
                "personality_detailed": "Подробный анализ числа личности...",
                "forecast": "Ваш прогноз на ближайший период выглядит благоприятным. Рекомендуется обратить внимание на развитие творческих навыков и укрепление деловых связей.",
                "recommendations": "Персональные рекомендации для вашего развития..."
            },
            "full_report": {
                "introduction": "Этот нумерологический отчет создан на основе ваших персональных данных и содержит глубокий анализ вашей личности, потенциала и жизненного пути.",
                "life_path_interpretation": f"Число жизненного пути {life_path} указывает на вашу независимость и лидерские качества.",
                "expression_interpretation": f"Число выражения {expression} раскрывает ваш творческий потенциал и ораторские способности.",
                "soul_interpretation": f"Число души {soul_urge} показывает ваши внутренние мотивы и стремления.",
                "personality_interpretation": f"Число личности {personality} отражает вашу внешнюю проекцию и то, как вас воспринимают окружающие.",
                "life_path_detailed": "Подробный анализ числа жизненного пути...",
                "expression_detailed": "Подробный анализ числа выражения...",
                "soul_detailed": "Подробный анализ числа души...",
                "personality_detailed": "Подробный анализ числа личности...",
                "forecast": "Ваш прогноз на ближайший период выглядит благоприятным. Рекомендуется обратить внимание на развитие творческих навыков и укрепление деловых связей.",
                "recommendations": "Персональные рекомендации для вашего развития..."
            }
        }
    
    elif "numerology-compatibility" in webhook_url:
        report_type = data.get("type", "mini")
        compatibility_score = 75  # Тестовое значение

        if report_type == "mini":
            return {
                "compatibility_mini_report": f"""
Краткий анализ совместимости (тестовый режим):

Общая совместимость: {compatibility_score}%
Ваша пара обладает хорошим потенциалом для гармоничных отношений. Вы дополняете друг друга в ключевых аспектах и имеете схожие ценности.

Сильные стороны: взаимопонимание, поддержка, схожие цели.
Возможные трудности: разные подходы к решению проблем.

Для получения полного анализа совместимости рекомендуем заказать подробный отчет.
                """
            }
        else:
            return {
                "compatibility": {
                    "intro": "Этот отчет о совместимости основан на нумерологическом анализе обоих партнеров.",
                    "score": compatibility_score,
                    "strengths": "Ваша пара обладает сильными сторонами в области коммуникации и взаимной поддержки...",
                    "challenges": "Возможные трудности могут возникать в сфере распределения ответственности...",
                    "recommendations": "Рекомендации для улучшения отношений..."
                },
                "compatibility_report": {
                    "intro": "Этот отчет о совместимости основан на нумерологическом анализе обоих партнеров.",
                    "score": compatibility_score,
                    "strengths": "Ваша пара обладает сильными сторонами в области коммуникации и взаимной поддержки...",
                    "challenges": "Возможные трудности могут возникать в сфере распределения ответственности...",
                    "recommendations": "Рекомендации для улучшения отношений..."
                }
            }
    
    elif "weekly-forecast" in webhook_url:
        return {
            "forecast": """
Еженедельный прогноз (тестовый режим):

Эта неделя будет благоприятна для новых начинаний и развития творческих проектов. Ваша энергия находится на высоком уровне, что позволит эффективно решать поставленные задачи.

Благоприятные дни: вторник, пятница
Сложные дни: среда

Совет недели: обратите внимание на свою интуицию, она может подсказать верное решение в сложной ситуации.
            """
        }
    
    # Если тип запроса не определен, возвращаем базовый ответ
    return {"message": "Тестовый ответ сгенерирован успешно"}