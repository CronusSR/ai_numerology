# interpret.py - модуль для интеграции с n8n и AI
import aiohttp
import json
import logging
import traceback
from typing import Dict, Any, Optional, Union
from datetime import datetime

import os  # оставьте если он нужен для других целей
from config import (
    TEST_MODE, 
    USE_EXTERNAL_WEBHOOK, 
    EXTERNAL_WEBHOOK_URL, 
    N8N_BASE_URL, 
    EXPECT_TEXT_RESPONSE,
    N8N_LOGS_DIR
)

N8N_LOGS_DIR = os.getenv("N8N_LOGS_DIR", "./n8n_logs")

def save_n8n_exchange(data: Dict[str, Any], response: Dict[str, Any], report_type: str) -> str:
    """
    Сохраняет данные обмена с n8n в файл для отладки и мониторинга.
    
    Args:
        data: Отправленные данные
        response: Полученный ответ
        report_type: Тип отчета
        
    Returns:
        str: Путь к созданному файлу
    """
    try:
        # Создаем директорию, если она не существует
        os.makedirs(N8N_LOGS_DIR, exist_ok=True)
        
        # Создаем поддиректорию по типу отчета
        type_dir = os.path.join(N8N_LOGS_DIR, report_type)
        os.makedirs(type_dir, exist_ok=True)
        
        # Формируем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  # Используем datetime.now()
        filename = f"{timestamp}_exchange.json"
        filepath = os.path.join(type_dir, filename)
        
        # Формируем данные для сохранения
        exchange_data = {
            "timestamp": datetime.now().isoformat(),  # Используем datetime.now()
            "report_type": report_type,
            "sent_data": data,
            "received_data": response,
            "is_test_mode": TEST_MODE
        }
        
        # Сохраняем в файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(exchange_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранен обмен данными с n8n: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Ошибка при сохранении обмена данными с n8n: {e}")
        return ""
# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL для интеграции с n8n
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")

# Таймаут для запросов (в секундах)
REQUEST_TIMEOUT = 60

# Режим работы и настройки
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
USE_EXTERNAL_WEBHOOK = os.getenv("USE_EXTERNAL_WEBHOOK", "true").lower() == "true"
EXPECT_TEXT_RESPONSE = os.getenv("EXPECT_TEXT_RESPONSE", "true").lower() == "true"

logger = logging.getLogger(__name__)
logger.info(f"interpret.py: настройки модуля:")
logger.info(f"N8N_BASE_URL: {N8N_BASE_URL}")
logger.info(f"EXTERNAL_WEBHOOK_URL: {EXTERNAL_WEBHOOK_URL}")
logger.info(f"USE_EXTERNAL_WEBHOOK: {USE_EXTERNAL_WEBHOOK}")
logger.info(f"EXPECT_TEXT_RESPONSE: {EXPECT_TEXT_RESPONSE}")
logger.info(f"TEST_MODE: {TEST_MODE}")

async def send_to_n8n_for_interpretation(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Отправляет данные на интерпретацию через n8n или внешний webhook в зависимости от типа отчета.
    
    Args:
        data: Словарь с нумерологическими расчетами
        report_type: Тип отчета ('mini', 'full', 'compatibility_mini', 'compatibility', 'weekly')
        
    Returns:
        Словарь с результатами интерпретации или пустой словарь в случае ошибки
    """
    try:
        # Если включен тестовый режим, генерируем тестовые ответы
        if TEST_MODE:
            test_response = generate_test_response(data, report_type)
            # Сохраняем обмен данными в тестовом режиме
            save_n8n_exchange(data, test_response, f"{report_type}_test")
            return test_response
        
        # Готовим данные для отправки
        webhook_url = EXTERNAL_WEBHOOK_URL if USE_EXTERNAL_WEBHOOK else f"{N8N_BASE_URL}/webhook/numerology"
        
        # Подготавливаем запрос с данными отчета
        request_data = {'report_type': report_type}
        
        # Если у нас есть расширенные данные в новом формате
        if "advanced_data" in data and "report_text" in data:
            # Отправляем только Markdown отчет и основные данные
            request_data.update({
                'report_text': data.get("report_text", ""),
                'core_data': {
                    'birthdate': data.get('birth_data', {}).get('date', ''),
                    'fio': data.get('fio', ''),
                    'life_path': data.get('life_path', 0),
                    'expression': data.get('expression', 0),
                    'soul_urge': data.get('soul_urge', 0),
                    'personality': data.get('personality', 0)
                }
            })
        elif "person1" in data and "person2" in data:
            # Отчет о совместимости
            request_data.update({
                'report_text': data.get('report_text', ''),
                'compatibility': data.get('compatibility', {}),
                'karmic_connection': data.get('karmic_connection', False),
                'challenges': data.get('challenges', [])
            })
        else:
            # Стандартные данные для старого формата
            request_data.update(data)
        
        logger.info(f"Отправка данных для интерпретации отчета типа: {report_type}")
        
        # Отправляем запрос
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/plain, */*"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=request_data,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            ) as response:
                status = response.status
                logger.info(f"Получен ответ с кодом: {status}")
                
                if status == 200:
                    # Проверяем тип контента
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        try:
                            result = await response.json()
                            logger.info(f"Успешный JSON ответ от webhook")
                            # Сохраняем обмен данными
                            save_n8n_exchange(request_data, result, report_type)
                            return result
                        except Exception as json_error:
                            logger.error(f"Ошибка при парсинге JSON: {json_error}")
                    
                    # Если ожидается текстовый ответ
                    if EXPECT_TEXT_RESPONSE or 'text' in content_type:
                        text = await response.text()
                        logger.info(f"Получен текстовый ответ длиной {len(text)} символов")
                        
                        # Форматируем ответ в зависимости от типа отчета
                        formatted_response = {}
                        if report_type == 'mini':
                            formatted_response = {"mini_report": text}
                        elif report_type == 'full':
                            formatted_response = {"full_report": parse_text_to_full_report(text)}
                        elif report_type == 'compatibility_mini':
                            formatted_response = {"compatibility_mini_report": text}
                        elif report_type == 'compatibility':
                            formatted_response = {"compatibility_report": parse_text_to_compatibility_report(text)}
                        elif report_type == 'weekly':
                            formatted_response = {"weekly_forecast": text}
                        else:
                            formatted_response = {"message": text}
                        
                        # Сохраняем обмен данными
                        save_n8n_exchange(request_data, {"text_response": text, "formatted": formatted_response}, report_type)
                        return formatted_response
                
                # Если ответ не успешный, возвращаем тестовые данные и сохраняем ошибку
                logger.warning(f"Ошибка от webhook или неверный формат ответа. Статус: {status}")
                error_text = await response.text()
                error_response = generate_test_response(data, report_type)
                save_n8n_exchange(request_data, {"error": True, "status": status, "error_text": error_text}, f"{report_type}_error")
                return error_response
                
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка подключения к webhook: {e}")
        error_response = generate_test_response(data, report_type)
        save_n8n_exchange(data, {"error": True, "message": str(e)}, f"{report_type}_connection_error")
        return error_response
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отправке данных: {e}")
        logger.error(traceback.format_exc())
        error_response = generate_test_response(data, report_type)
        save_n8n_exchange(data, {"error": True, "message": str(e)}, f"{report_type}_general_error")
        return error_response


def parse_text_to_full_report(text: str) -> Dict[str, Any]:
    """
    Разбирает текстовый ответ в структурированный формат для полного отчета.
    """
    # Базовая структура отчета
    report = {
        "introduction": "Персональный нумерологический анализ на основе ваших данных.",
        "life_path_interpretation": "Интерпретация числа жизненного пути.",
        "expression_interpretation": "Интерпретация числа выражения.",
        "soul_interpretation": "Интерпретация числа души.",
        "personality_interpretation": "Интерпретация числа личности.",
        "life_path_detailed": "Подробный анализ числа жизненного пути.",
        "expression_detailed": "Подробный анализ числа выражения.",
        "soul_detailed": "Подробный анализ числа души.",
        "personality_detailed": "Подробный анализ числа личности.",
        "forecast": "Прогноз на ближайшее время.",
        "recommendations": "Рекомендации для вашего развития."
    }
    
    # Если получен текст, используем его как введение и замещаем общие поля
    if text:
        # Разбиваем текст на секции
        sections = text.split("\n\n")
        if len(sections) >= 3:
            report["introduction"] = sections[0]
            report["life_path_detailed"] = "\n".join(sections[1:3])
            report["recommendations"] = sections[-1] if len(sections) > 3 else "Рекомендации будут предоставлены в полном отчете."
    
    return report


def parse_text_to_compatibility_report(text: str) -> Dict[str, Any]:
    """
    Разбирает текстовый ответ в структурированный формат для отчета о совместимости.
    """
    # Базовая структура отчета о совместимости
    report = {
        "intro": "Анализ совместимости на основе нумерологических расчетов.",
        "score": 75,  # Значение по умолчанию
        "strengths": "Сильные стороны отношений.",
        "challenges": "Возможные трудности в отношениях.",
        "recommendations": "Рекомендации для улучшения отношений."
    }
    
    # Если получен текст, обрабатываем его
    if text:
        # Попытка извлечь процент совместимости (ищем число и символ %)
        import re
        percent_matches = re.findall(r'(\d+(?:\.\d+)?)%', text)
        if percent_matches:
            try:
                report["score"] = float(percent_matches[0])
            except ValueError:
                pass
        
        # Разбиваем текст на секции
        sections = text.split("\n\n")
        if len(sections) >= 1:
            report["intro"] = sections[0]
        if len(sections) >= 2:
            report["strengths"] = sections[1]
        if len(sections) >= 3:
            report["challenges"] = sections[2]
        if len(sections) >= 4:
            report["recommendations"] = sections[3]
    
    return report


def generate_test_response(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Генерирует тестовый ответ для различных типов запросов в режиме тестирования.
    """
    # Получаем нужные данные из запроса
    life_path = data.get("life_path", 1)
    expression = data.get("expression", 1)
    
    # Если это отчет о совместимости
    if report_type in ['compatibility_mini', 'compatibility']:
        # Получаем информацию о людях, если доступна
        if "person1" in data and "person2" in data:
            person1 = data.get("person1", {})
            person2 = data.get("person2", {})
            
            person1_name = person1.get("raw_data", {}).get("fio", "Человек 1")
            person2_name = person2.get("raw_data", {}).get("fio", "Человек 2")
        else:
            person1_name = "Человек 1"
            person2_name = "Человек 2"
        
        compatibility_percent = data.get("compatibility", {}).get("percent", 75)  # Берем процент из данных или 75% по умолчанию

        if report_type == 'compatibility_mini':
            return {
                "compatibility_mini_report": f"""
Краткий анализ совместимости:

Общая совместимость между {person1_name} и {person2_name}: {compatibility_percent}%

Ваша пара обладает хорошим потенциалом для гармоничных отношений. Вы дополняете друг друга в ключевых аспектах и имеете схожие ценности.

Сильные стороны: взаимопонимание, поддержка, схожие цели.
Возможные трудности: разные подходы к решению проблем.

Для получения полного анализа совместимости рекомендуем заказать подробный отчет.
                """
            }
        else:
            return {
                "compatibility_report": {
                    "intro": f"Анализ совместимости между {person1_name} и {person2_name} показывает общую совместимость {compatibility_percent}%.",
                    "score": compatibility_percent,
                    "strengths": "Вы дополняете друг друга энергетически, создавая баланс между индивидуальными качествами. Ваше взаимопонимание основано на схожих ценностях и жизненных целях.",
                    "challenges": "Возможны разногласия из-за различных подходов к решению проблем. Вам обоим нужно работать над терпением и гибкостью в отношениях.",
                    "recommendations": "Регулярно обсуждайте ваши цели и планы, чтобы быть на одной волне. Помните, что каждый из вас обладает уникальными качествами, которые дополняют друг друга."
                }
            }
    
    # Если это мини-отчет
    elif report_type == 'mini':
        # Используем отчет в формате Markdown, если он доступен
        if "report_text" in data:
            mini_report = f"""
Краткий нумерологический анализ:

{data.get('report_text', '').split('##')[0].strip()}

Ваше число жизненного пути: {life_path}
Число выражения: {expression}

Для получения полного анализа рекомендуем заказать подробный PDF-отчет.
            """
        else:
            mini_report = f"""
Краткий нумерологический анализ:

Ваше число жизненного пути: {life_path}
Это число определяет вашу жизненную миссию и основные уроки, которые вам предстоит пройти. Вы обладаете сильным потенциалом лидера и первооткрывателя.

Число выражения: {expression}
Это число отражает ваши таланты и способы их реализации. Вы наделены творческим мышлением и умеете вдохновлять окружающих.

Для получения полного анализа рекомендуем заказать подробный PDF-отчет.
            """
        
        return {
            "mini_report": mini_report
        }
    
    # Если это полный отчет
    elif report_type == 'full':
        return {
            "full_report": {
                "introduction": f"Этот нумерологический отчет создан на основе ваших персональных данных и содержит глубокий анализ вашей личности, потенциала и жизненного пути.",
                "life_path_interpretation": f"Число жизненного пути {life_path} указывает на вашу независимость и лидерские качества.",
                "expression_interpretation": f"Число выражения {expression} раскрывает ваш творческий потенциал и ораторские способности.",
                "soul_interpretation": "Число души показывает ваши внутренние мотивы и стремления.",
                "personality_interpretation": "Число личности отражает вашу внешнюю проекцию и то, как вас воспринимают окружающие.",
                "life_path_detailed": f"Вы обладаете выраженными лидерскими качествами и способностью вдохновлять других. Ваша энергия и решительность помогают преодолевать препятствия.",
                "expression_detailed": "Вы имеете яркую индивидуальность и креативный подход к решению задач. Ваша коммуникабельность позволяет находить общий язык с разными людьми.",
                "soul_detailed": "Внутренне вы стремитесь к гармонии и балансу. Ваша интуиция помогает вам принимать верные решения в сложных ситуациях.",
                "personality_detailed": "Окружающие видят в вас надежного и ответственного человека. Вы умеете производить благоприятное первое впечатление.",
                "forecast": "В ближайшее время вам предстоит период активного роста и развития. Рекомендуется обратить внимание на новые возможности в профессиональной сфере.",
                "recommendations": "Развивайте свои коммуникативные навыки, они будут особенно полезны в ближайшем будущем. Уделите внимание духовному развитию и поиску внутреннего баланса."
            }
        }
    
    # Если это еженедельный прогноз
    elif report_type == 'weekly':
        return {
            "weekly_forecast": f"""
Еженедельный прогноз:

Эта неделя будет благоприятна для новых начинаний и развития творческих проектов. Ваша энергия находится на высоком уровне, что позволит эффективно решать поставленные задачи.

Благоприятные дни: вторник, пятница
Сложные дни: среда

Совет недели: обратите внимание на свою интуицию, она может подсказать верное решение в сложной ситуации.
            """
        }
    
    # Если тип запроса не определен, возвращаем базовый ответ
    return {"message": "Тестовый ответ сгенерирован успешно", "report_type": report_type}