"""
Модуль для интеграции с n8n и ИИ для интерпретации нумерологических расчетов.
Предоставляет функции для отправки данных расчетов на интерпретацию и получения результатов.
В текущей версии работает в автономном режиме, генерируя ответы локально.
"""

# interpret.py (обновленная версия)

import aiohttp
import json
import logging
import os
import traceback
from typing import Dict, Any, Optional, Union

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL для интеграции с n8n (старый URL, оставлен для совместимости)
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_WEBHOOK_URL = f"{N8N_BASE_URL}/webhook/c4f6a246-0e5f-4a92-b901-8018c98c11ff"

# URL для интеграции с новым внешним webhook
EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")

# Таймаут для запросов (в секундах)
REQUEST_TIMEOUT = 60

# Режим работы: используем внешний webhook
AUTONOMOUS_MODE = os.getenv("MOCK_N8N", "false").lower() == "true"
USE_EXTERNAL_WEBHOOK = os.getenv("USE_EXTERNAL_WEBHOOK", "true").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

logger.info(f"interpret.py: настройки модуля:")
logger.info(f"N8N_BASE_URL: {N8N_BASE_URL}")
logger.info(f"N8N_WEBHOOK_URL: {N8N_WEBHOOK_URL}")
logger.info(f"EXTERNAL_WEBHOOK_URL: {EXTERNAL_WEBHOOK_URL}")
logger.info(f"AUTONOMOUS_MODE: {AUTONOMOUS_MODE}")
logger.info(f"USE_EXTERNAL_WEBHOOK: {USE_EXTERNAL_WEBHOOK}")
logger.info(f"TEST_MODE: {TEST_MODE}")


async def send_to_n8n(webhook_url: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Отправляет данные на webhook n8n или внешний webhook и возвращает ответ.
    В автономном режиме генерирует ответы локально.
    
    Args:
        webhook_url: URL вебхука (не используется при USE_EXTERNAL_WEBHOOK=True)
        data: Словарь с данными для отправки
        
    Returns:
        Ответ от webhook в виде словаря или локально сгенерированные данные
    """
    if AUTONOMOUS_MODE:
        logger.info(f"Автономный режим: Генерация данных для запроса типа {data.get('report_type', 'unknown')}")
        return generate_test_response(webhook_url, data)

    # Определяем URL, который будем использовать
    actual_webhook_url = EXTERNAL_WEBHOOK_URL if USE_EXTERNAL_WEBHOOK else webhook_url
    
    # Добавляем тип отчета в данные, если его нет
    if 'report_type' not in data and webhook_url:
        if 'mini-report' in webhook_url:
            data['report_type'] = 'mini'
        elif 'full-report' in webhook_url:
            data['report_type'] = 'full'
        elif 'compatibility' in webhook_url:
            data['report_type'] = 'compatibility'
        elif 'weekly-forecast' in webhook_url:
            data['report_type'] = 'weekly'

    # Проверка доступности webhook
    logger.info(f"Отправка запроса на webhook для типа: {data.get('report_type', 'unknown')}")
    logger.info(f"URL запроса: {actual_webhook_url}")
    logger.debug(f"Данные запроса: {json.dumps(data, ensure_ascii=False, indent=2)}")

    # Попытка отправки реального запроса к webhook
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                actual_webhook_url,
                json=data,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            ) as response:
                status = response.status
                logger.info(f"Получен ответ с кодом: {status}")
                
                if status == 200:
                    try:
                        result = await response.json()
                        logger.info(f"Успешный ответ от webhook")
                        logger.debug(f"Структура ответа: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        return result
                    except Exception as json_error:
                        text = await response.text()
                        logger.error(f"Ошибка при парсинге JSON: {json_error}")
                        logger.error(f"Текст ответа: {text}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка от webhook: статус {status}, ответ: {error_text}")
                    
                    # Если ответ не успешный, генерируем тестовые данные вместо него
                    logger.warning("Использование тестовых данных из-за ошибки ответа")
                    return generate_test_response(webhook_url, data)
                    
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка подключения к webhook: {e}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        # В случае ошибки подключения генерируем тестовые данные
        logger.warning("Использование тестовых данных из-за ошибки подключения")
        return generate_test_response(webhook_url, data)
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отправке данных: {e}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        # В случае любой другой ошибки генерируем тестовые данные
        logger.warning("Использование тестовых данных из-за непредвиденной ошибки")
        return generate_test_response(webhook_url, data)


async def send_to_n8n_for_interpretation(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Отправляет данные на интерпретацию через n8n или внешний webhook в зависимости от типа отчета.
    
    Args:
        data: Словарь с нумерологическими расчетами
        report_type: Тип отчета ('mini', 'full', 'compatibility_mini', 'compatibility')
        
    Returns:
        Словарь с результатами интерпретации или пустой словарь в случае ошибки
    """
    try:
        # Добавляем тип отчета в данные
        request_data = {**data, 'report_type': report_type}
        
        logger.info(f"Запрос интерпретации для отчета типа: {report_type}")
        
        # Отправляем запрос
        result = await send_to_n8n("", request_data)
        
        # Добавьте отладочный вывод
        logger.info(f"Получен ответ: {json.dumps(result, ensure_ascii=False)[:200] if result else 'None'}...")
        
        if not result:
            logger.error(f"Не удалось получить интерпретацию для отчета типа: {report_type}")
            if report_type == 'mini':
                return {"mini_report": "Извините, не удалось получить интерпретацию. Пожалуйста, попробуйте позже."}
            elif report_type == 'full':
                return {"full_report": {"introduction": "Извините, не удалось получить интерпретацию."}}
            elif report_type == 'compatibility_mini':
                return {"compatibility_mini_report": "Извините, не удалось получить интерпретацию."}
            elif report_type == 'compatibility':
                return {"compatibility_report": {"introduction": "Извините, не удалось получить интерпретацию."}}
            else:
                return {}
        
        # Проверка наличия ожидаемых ключей в ответе
        expected_key = None
        if report_type == 'mini':
            expected_key = 'mini_report'
        elif report_type == 'full':
            expected_key = 'full_report'
        elif report_type == 'compatibility_mini':
            expected_key = 'compatibility_mini_report'
        elif report_type == 'compatibility':
            expected_key = 'compatibility_report'
        
        if expected_key and expected_key not in result:
            logger.warning(f"Ответ не содержит ожидаемого ключа '{expected_key}'. Попытка найти альтернативные ключи...")
            
            # Проверка альтернативных ключей или перенос данных из доступных ключей
            if 'message' in result:
                if report_type == 'mini':
                    return {"mini_report": result['message']}
                elif report_type == 'compatibility_mini':
                    return {"compatibility_mini_report": result['message']}
            
            # Если есть текстовое поле 'text' или 'content'
            for key in ['text', 'content', 'response', 'result']:
                if key in result:
                    if report_type == 'mini':
                        return {"mini_report": result[key]}
                    elif report_type == 'full':
                        return {"full_report": {"introduction": result[key]}}
                    elif report_type == 'compatibility_mini':
                        return {"compatibility_mini_report": result[key]}
                    elif report_type == 'compatibility':
                        return {"compatibility_report": {"intro": result[key]}}
            
            logger.error(f"Не удалось найти подходящий ключ в ответе: {json.dumps(result, ensure_ascii=False)}")
            
            # Возвращаем весь ответ как есть, возможно, он имеет правильную структуру
            return result
                
        return result
    except Exception as e:
        logger.error(f"Ошибка в send_to_n8n_for_interpretation: {e}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        
        # Возвращаем заполнитель в зависимости от типа отчета
        if report_type == 'mini':
            return {"mini_report": "Извините, произошла ошибка при получении интерпретации. Пожалуйста, попробуйте позже."}
        elif report_type == 'full':
            return {"full_report": {"introduction": "Извините, произошла ошибка при получении интерпретации."}}
        elif report_type == 'compatibility_mini':
            return {"compatibility_mini_report": "Извините, произошла ошибка при получении интерпретации."}
        elif report_type == 'compatibility':
            return {"compatibility_report": {"introduction": "Извините, произошла ошибка при получении интерпретации."}}
        else:
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