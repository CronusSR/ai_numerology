# interpret.py - обновленный модуль для интеграции с n8n
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

# URL для интеграции с n8n
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_WEBHOOK_URL = f"{N8N_BASE_URL}/webhook/numerology"

# URL для интеграции с внешним webhook
EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")

# Таймаут для запросов (в секундах)
REQUEST_TIMEOUT = 60

# Режим работы и настройки
AUTONOMOUS_MODE = os.getenv("MOCK_N8N", "false").lower() == "true"
USE_EXTERNAL_WEBHOOK = os.getenv("USE_EXTERNAL_WEBHOOK", "true").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
EXPECT_TEXT_RESPONSE = os.getenv("EXPECT_TEXT_RESPONSE", "true").lower() == "true"

logger.info(f"interpret.py: настройки модуля:")
logger.info(f"N8N_BASE_URL: {N8N_BASE_URL}")
logger.info(f"N8N_WEBHOOK_URL: {N8N_WEBHOOK_URL}")
logger.info(f"EXTERNAL_WEBHOOK_URL: {EXTERNAL_WEBHOOK_URL}")
logger.info(f"AUTONOMOUS_MODE: {AUTONOMOUS_MODE}")
logger.info(f"USE_EXTERNAL_WEBHOOK: {USE_EXTERNAL_WEBHOOK}")
logger.info(f"EXPECT_TEXT_RESPONSE: {EXPECT_TEXT_RESPONSE}")
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
            "Accept": "application/json, text/plain, */*"  # Принимаем любой тип ответа
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
                    # Проверяем тип контента
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        # Пробуем распарсить JSON
                        try:
                            result = await response.json()
                            logger.info(f"Успешный JSON ответ от webhook")
                            logger.debug(f"Структура ответа: {json.dumps(result, ensure_ascii=False, indent=2)}")
                            return result
                        except Exception as json_error:
                            logger.error(f"Ошибка при парсинге JSON: {json_error}")
                    
                    # Если ожидается текстовый ответ или не удалось распарсить JSON
                    if EXPECT_TEXT_RESPONSE or 'text/html' in content_type or 'text/plain' in content_type:
                        text = await response.text()
                        logger.info(f"Получен текстовый ответ: {text[:200]}...")
                        
                        # Форматируем текстовый ответ в структуру, ожидаемую ботом
                        report_type = data.get('report_type', 'unknown')
                        
                        # Импортируем функции парсинга из модуля numerology_core
                        from numerology_core import parse_text_to_full_report, parse_text_to_compatibility_report
                        
                        if report_type == 'mini':
                            return {"mini_report": text}
                        elif report_type == 'full':
                            # Разбиваем текст на основные разделы для полного отчета
                            full_report = parse_text_to_full_report(text)
                            return {"full_report": full_report}
                        elif report_type == 'compatibility_mini':
                            return {"compatibility_mini_report": text}
                        elif report_type == 'compatibility':
                            # Разбиваем текст на основные разделы для отчета о совместимости
                            compatibility_report = parse_text_to_compatibility_report(text)
                            return {"compatibility_report": compatibility_report}
                        else:
                            return {"message": text}
                    
                    logger.error(f"Неизвестный формат ответа")
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
        
        # Проверяем, есть ли расширенные данные и отчет в Markdown
        if "advanced_data" in data and "report_text" in data:
            # Упрощаем запрос - отправляем только нужные данные и текст отчета
            request_data = {
                'report_type': report_type,
                'report_text': data.get("report_text", ""),
                'core_data': {
                    'birthdate': data.get('birth_data', {}).get('date', ''),
                    'fio': data.get('fio', ''),
                    'life_path': data.get('life_path', 0),
                    'expression': data.get('expression', 0),
                    'soul_urge': data.get('soul_urge', 0),
                    'personality': data.get('personality', 0)
                }
            }
        
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
        webhook_url: URL вебхука n8n (не используется в новой версии)
        data: Словарь с данными для отправки
        
    Returns:
        Тестовый ответ в зависимости от типа запроса
    """
    report_type = data.get('report_type', 'unknown')
    
    if report_type == 'mini':
        # Используем report_text, если он доступен
        if "report_text" in data:
            mini_report = f"""
Краткий нумерологический анализ по корневой дате:

{data.get('report_text', '')}

Для получения полного анализа рекомендуем заказать подробный PDF-отчет, содержащий более глубокую интерпретацию ваших нумерологических показателей и персональные рекомендации.
            """
        else:
            # Иначе формируем отчет на основе базовых параметров
            life_path = data.get("life_path", 1)
            expression = data.get("expression", 1)
            mini_report = f"""
Ваш мини-отчет (тестовый режим):

Число жизненного пути: {life_path}
Вы обладаете сильным потенциалом лидера и первооткрывателя. Ваша независимость и оригинальность мышления помогают находить необычные решения стандартных задач.

Число выражения: {expression}
Вы наделены творческим мышлением и умеете вдохновлять окружающих своим энтузиазмом. Ваша коммуникабельность помогает налаживать контакты в различных сферах.

Для получения полного анализа рекомендуем заказать подробный PDF-отчет, содержащий более глубокую интерпретацию ваших нумерологических показателей и персональные рекомендации.
            """
        
        return {
            "mini_report": mini_report
        }
    
    elif report_type == 'full':
        # Используем report_text, если он доступен
        if "report_text" in data:
            interpretation_text = data.get('report_text', '')
        else:
            # Иначе формируем отчет на основе базовых параметров
            life_path = data.get("life_path", 1)
            expression = data.get("expression", 1)
            soul_urge = data.get("soul_urge", 1)
            personality = data.get("personality", 1)
            
            interpretation_text = f"""
# Параметры по корневой дате
## Параметры "Дт"
### Аркан_Дт={life_path}
### Процент_Дт={40.5}
## Параметры "Мт"
### Аркан_Мт={expression}
### Процент_Мт={22.5}
### Тип_Мт=Либеральный
## Параметры "Гт"
### Аркан_Гт={soul_urge}
### Процент_Гт={36.0}
## Параметры "МЧ"
### Аркан_МЧ={personality}
### Процент_МЧ={99.0}
## Параметры "СТ"
### Аркан_СТ=8
            """
        
        # Импортируем функцию парсинга из модуля numerology_core
        from numerology_core import parse_text_to_full_report
        
        # Создаем структурированный ответ
        full_report = parse_text_to_full_report(interpretation_text)
        
        return {
            "full_report": full_report
        }
    
    elif report_type in ['compatibility_mini', 'compatibility']:
        # Получаем информацию о людях, если она доступна
        if "person1" in data and "person2" in data:
            person1 = data.get("person1", {})
            person2 = data.get("person2", {})
            
            person1_name = person1.get("fio", "Человек 1")
            person2_name = person2.get("fio", "Человек 2")
        else:
            person1_name = "Человек 1"
            person2_name = "Человек 2"
        
        compatibility_score = data.get("compatibility", {}).get("percent", 75)  # Берем процент из данных или 75% по умолчанию

        if report_type == 'compatibility_mini':
            return {
                "compatibility_mini_report": f"""
Краткий анализ совместимости (тестовый режим):

Общая совместимость между {person1_name} и {person2_name}: {compatibility_score}%

Ваша пара обладает хорошим потенциалом для гармоничных отношений. Вы дополняете друг друга в ключевых аспектах и имеете схожие ценности.

Сильные стороны: взаимопонимание, поддержка, схожие цели.
Возможные трудности: разные подходы к решению проблем.

Для получения полного анализа совместимости рекомендуем заказать подробный отчет.
                """
            }
        else:
            # Импортируем функцию парсинга из модуля numerology_core
            from numerology_core import parse_text_to_compatibility_report
            
            compatibility_text = f"""# Анализ совместимости
## Общие параметры
### Совместимость_Общая={compatibility_score}%
### Совместимость_Жизненные_Пути=70.5%
### Совместимость_Эмоциональная=85.5%
### Совместимость_Интеллектуальная=65.0%
### Совместимость_Физическая=80.0%
### Кармическая_Связь=Да"""
            
            compatibility_report = parse_text_to_compatibility_report(compatibility_text)
            
            return {
                "compatibility_report": compatibility_report
            }
    
    elif report_type == 'weekly':
        return {
            "forecast": f"""
Еженедельный прогноз (тестовый режим):

Эта неделя будет благоприятна для новых начинаний и развития творческих проектов. Ваша энергия находится на высоком уровне, что позволит эффективно решать поставленные задачи.

Благоприятные дни: вторник, пятница
Сложные дни: среда

Совет недели: обратите внимание на свою интуицию, она может подсказать верное решение в сложной ситуации.
            """
        }
    
    # Если тип запроса не определен, возвращаем базовый ответ
    return {"message": "Автономный ответ сгенерирован успешно", "report_type": report_type}