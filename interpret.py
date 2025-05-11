"""
Модуль для интеграции с n8n и ИИ для интерпретации нумерологических расчетов.
Предоставляет функции для отправки данных расчетов на интерпретацию и получения результатов.
В текущей версии работает в автономном режиме, генерируя ответы локально.
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

# URL для интеграции с n8n (для будущего использования)
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://n8n:5678")
MINI_REPORT_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-mini-report"
FULL_REPORT_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-full-report"
COMPATIBILITY_WEBHOOK = f"{N8N_BASE_URL}/webhook/numerology-compatibility"
WEEKLY_FORECAST_WEBHOOK = f"{N8N_BASE_URL}/webhook/weekly-forecast"

# Таймаут для запросов (в секундах)
REQUEST_TIMEOUT = 60

# Режим работы: автономный режим включен по умолчанию из-за проблем с подключением к n8n
AUTONOMOUS_MODE = True
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"


async def send_to_n8n(webhook_url: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Отправляет данные на webhook n8n и возвращает ответ.
    В автономном режиме генерирует ответы локально.
    
    Args:
        webhook_url: URL вебхука n8n
        data: Словарь с данными для отправки
        
    Returns:
        Ответ от n8n в виде словаря или локально сгенерированные данные
    """
    # В автономном режиме или тестовом режиме генерируем данные локально
    if AUTONOMOUS_MODE or TEST_MODE:
        logger.info(f"Автономный режим: Генерация данных для {webhook_url}")
        return generate_test_response(webhook_url, data)

    # Попытка отправки реального запроса к n8n
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
                    # Если ответ не успешный, генерируем тестовые данные вместо него
                    return generate_test_response(webhook_url, data)
    except aiohttp.ClientError as e:
        logger.error(f"Connection error to n8n: {e}")
        # В случае ошибки подключения генерируем тестовые данные
        return generate_test_response(webhook_url, data)
    except Exception as e:
        logger.error(f"Unexpected error sending data to n8n: {e}")
        # В случае любой другой ошибки генерируем тестовые данные
        return generate_test_response(webhook_url, data)


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
            logger.info(f"Запрос интерпретации для мини-отчета")
            result = await send_to_n8n(MINI_REPORT_WEBHOOK, data)
            if not result:
                logger.error("Failed to get mini report interpretation")
                return {"mini_report": "Извините, не удалось получить интерпретацию. Пожалуйста, попробуйте позже."}
            return result
        elif report_type == 'full':
            logger.info(f"Запрос интерпретации для полного отчета")
            result = await send_to_n8n(FULL_REPORT_WEBHOOK, data)
            if not result:
                logger.error("Failed to get full report interpretation")
                return {"full_report": {"introduction": "Извините, не удалось получить интерпретацию."}}
            return result
        elif report_type == 'compatibility_mini':
            logger.info(f"Запрос интерпретации для мини-отчета о совместимости")
            result = await send_to_n8n(COMPATIBILITY_WEBHOOK, {"type": "mini", **data})
            if not result:
                logger.error("Failed to get compatibility mini report interpretation")
                return {"compatibility_mini_report": "Извините, не удалось получить интерпретацию."}
            return result
        elif report_type == 'compatibility':
            logger.info(f"Запрос интерпретации для полного отчета о совместимости")
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
Ваш мини-отчет (автономный режим):

Число жизненного пути: {life_path}
Вы обладаете сильным потенциалом лидера и первооткрывателя. Ваша независимость и оригинальность мышления помогают находить необычные решения стандартных задач.

Число выражения: {expression}
Вы наделены творческим мышлением и умеете вдохновлять окружающих своим энтузиазмом. Ваша коммуникабельность помогает налаживать контакты в различных сферах.

Для получения полного анализа рекомендуем заказать подробный PDF-отчет, содержащий более глубокую интерпретацию ваших нумерологических показателей и персональные рекомендации.
            """,
            "mini_report": f"""
Ваш мини-отчет (автономный режим):

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
                "life_path_detailed": f"Подробный анализ числа жизненного пути {life_path}: Вы обладаете выраженными лидерскими качествами и способностью вдохновлять других. Ваша энергия и решительность помогают преодолевать препятствия.",
                "expression_detailed": f"Подробный анализ числа выражения {expression}: Вы имеете яркую индивидуальность и креативный подход к решению задач. Ваша коммуникабельность позволяет находить общий язык с разными людьми.",
                "soul_detailed": f"Подробный анализ числа души {soul_urge}: Внутренне вы стремитесь к гармонии и балансу. Ваша интуиция помогает вам принимать верные решения в сложных ситуациях.",
                "personality_detailed": f"Подробный анализ числа личности {personality}: Окружающие видят в вас надежного и ответственного человека. Вы умеете производить благоприятное первое впечатление.",
                "forecast": "В ближайшее время вам предстоит период активного роста и развития. Рекомендуется обратить внимание на новые возможности в профессиональной сфере.",
                "recommendations": "Развивайте свои коммуникативные навыки, они будут особенно полезны в ближайшем будущем. Уделите внимание духовному развитию и поиску внутреннего баланса."
            },
            "full_report": {
                "introduction": "Этот нумерологический отчет создан на основе ваших персональных данных и содержит глубокий анализ вашей личности, потенциала и жизненного пути.",
                "life_path_interpretation": f"Число жизненного пути {life_path} указывает на вашу независимость и лидерские качества.",
                "expression_interpretation": f"Число выражения {expression} раскрывает ваш творческий потенциал и ораторские способности.",
                "soul_interpretation": f"Число души {soul_urge} показывает ваши внутренние мотивы и стремления.",
                "personality_interpretation": f"Число личности {personality} отражает вашу внешнюю проекцию и то, как вас воспринимают окружающие.",
                "life_path_detailed": f"Подробный анализ числа жизненного пути {life_path}: Вы обладаете выраженными лидерскими качествами и способностью вдохновлять других. Ваша энергия и решительность помогают преодолевать препятствия.",
                "expression_detailed": f"Подробный анализ числа выражения {expression}: Вы имеете яркую индивидуальность и креативный подход к решению задач. Ваша коммуникабельность позволяет находить общий язык с разными людьми.",
                "soul_detailed": f"Подробный анализ числа души {soul_urge}: Внутренне вы стремитесь к гармонии и балансу. Ваша интуиция помогает вам принимать верные решения в сложных ситуациях.",
                "personality_detailed": f"Подробный анализ числа личности {personality}: Окружающие видят в вас надежного и ответственного человека. Вы умеете производить благоприятное первое впечатление.",
                "forecast": "В ближайшее время вам предстоит период активного роста и развития. Рекомендуется обратить внимание на новые возможности в профессиональной сфере.",
                "recommendations": "Развивайте свои коммуникативные навыки, они будут особенно полезны в ближайшем будущем. Уделите внимание духовному развитию и поиску внутреннего баланса."
            }
        }
    
    elif "numerology-compatibility" in webhook_url:
        report_type = data.get("type", "mini")
        compatibility_score = 75  # Тестовое значение
        
        # Получаем информацию о людях, если она доступна
        person1_name = data.get("person1", {}).get("fio", "Человек 1")
        person2_name = data.get("person2", {}).get("fio", "Человек 2")

        if report_type == "mini":
            return {
                "compatibility_mini_report": f"""
Краткий анализ совместимости (автономный режим):

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
                    "intro": f"Этот отчет о совместимости основан на нумерологическом анализе {person1_name} и {person2_name}.",
                    "score": compatibility_score,
                    "strengths": "Ваша пара обладает сильными сторонами в области коммуникации и взаимной поддержки. Вы хорошо дополняете друг друга и имеете схожие ценности и жизненные цели.",
                    "challenges": "Возможные трудности могут возникать в сфере распределения ответственности и принятия важных решений. Разные подходы к решению проблем могут создавать напряжение.",
                    "recommendations": "Для укрепления отношений рекомендуется больше времени уделять совместным занятиям и открытому обсуждению ваших целей и ожиданий. Важно научиться уважать и принимать различия друг друга."
                },
                "compatibility_report": {
                    "intro": f"Этот отчет о совместимости основан на нумерологическом анализе {person1_name} и {person2_name}.",
                    "score": compatibility_score,
                    "strengths": "Ваша пара обладает сильными сторонами в области коммуникации и взаимной поддержки. Вы хорошо дополняете друг друга и имеете схожие ценности и жизненные цели.",
                    "challenges": "Возможные трудности могут возникать в сфере распределения ответственности и принятия важных решений. Разные подходы к решению проблем могут создавать напряжение.",
                    "recommendations": "Для укрепления отношений рекомендуется больше времени уделять совместным занятиям и открытому обсуждению ваших целей и ожиданий. Важно научиться уважать и принимать различия друг друга."
                }
            }
    
    elif "weekly-forecast" in webhook_url:
        return {
            "forecast": """
Еженедельный прогноз (автономный режим):

Эта неделя будет благоприятна для новых начинаний и развития творческих проектов. Ваша энергия находится на высоком уровне, что позволит эффективно решать поставленные задачи.

Благоприятные дни: вторник, пятница
Сложные дни: среда

Совет недели: обратите внимание на свою интуицию, она может подсказать верное решение в сложной ситуации.
            """
        }
    
    # Если тип запроса не определен, возвращаем базовый ответ
    return {"message": "Автономный ответ сгенерирован успешно"}