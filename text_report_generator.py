"""
Улучшенный модуль для генерации текстовых отчетов.
Решает проблемы с форматированием и добавляет структурированное хранение.
"""

import os
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, Union

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к директории для сохранения отчетов
REPORTS_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')

# Создаем директорию для хранения отчетов, если она не существует
os.makedirs(REPORTS_PATH, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов
    """
    # Заменяем недопустимые символы на нижнее подчеркивание
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Заменяем пробелы на нижнее подчеркивание
    sanitized = sanitized.replace(' ', '_')
    return sanitized

def get_user_directory(user_data: Dict[str, Any]) -> str:
    """
    Создает директорию для хранения отчетов пользователя
    """
    # Получаем ФИО пользователя или используем ID, если ФИО отсутствует
    user_name = user_data.get('fio', f"user_{user_data.get('id', 'unknown')}")
    sanitized_name = sanitize_filename(user_name)
    
    # Создаем путь к директории пользователя
    user_dir = os.path.join(REPORTS_PATH, sanitized_name)
    
    # Создаем директорию, если она не существует
    os.makedirs(user_dir, exist_ok=True)
    
    return user_dir

def format_date(date_value: Union[str, datetime.date]) -> str:
    """
    Форматирует дату в читаемый формат.
    """
    if isinstance(date_value, str):
        try:
            # Пробуем разные форматы
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
                try:
                    date_obj = datetime.strptime(date_value, fmt)
                    return date_obj.strftime('%d.%m.%Y')
                except ValueError:
                    continue
            # Если ни один формат не подошел, возвращаем как есть
            return date_value
        except Exception:
            return date_value
    elif hasattr(date_value, 'strftime'):
        # Если это объект даты
        return date_value.strftime('%d.%m.%Y')
    else:
        return str(date_value)

def extract_data_from_interpretation(interpretation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Извлекает данные из различных форматов интерпретации
    """
    result = {}
    
    # Проверка каждого возможного формата ответа
    full_report = interpretation_data.get('full_report', {})
    compatibility_report = interpretation_data.get('compatibility_report', {})
    
    # Введение
    result['introduction'] = interpretation_data.get('introduction', '')
    if not result['introduction'] and isinstance(full_report, dict):
        result['introduction'] = full_report.get('introduction', '')
    
    # Интерпретации для каждого числа
    for key in ['life_path', 'expression', 'soul', 'personality']:
        # Основные интерпретации
        interp_key = f'{key}_interpretation'
        result[interp_key] = interpretation_data.get(interp_key, '')
        if not result[interp_key] and isinstance(full_report, dict):
            result[interp_key] = full_report.get(interp_key, '')
        
        # Детальные интерпретации
        detailed_key = f'{key}_detailed'
        result[detailed_key] = interpretation_data.get(detailed_key, '')
        if not result[detailed_key] and isinstance(full_report, dict):
            result[detailed_key] = full_report.get(detailed_key, '')
    
    # Прогноз и рекомендации
    result['forecast'] = interpretation_data.get('forecast', '')
    if not result['forecast'] and isinstance(full_report, dict):
        result['forecast'] = full_report.get('forecast', '')
    
    result['recommendations'] = interpretation_data.get('recommendations', '')
    if not result['recommendations'] and isinstance(full_report, dict):
        result['recommendations'] = full_report.get('recommendations', '')
    
    # Данные совместимости
    if isinstance(compatibility_report, dict):
        compat_keys = ['intro', 'score', 'strengths', 'challenges', 'recommendations']
        for key in compat_keys:
            compat_key = f'compatibility_{key}'
            result[compat_key] = compatibility_report.get(key, '')
    
    return result

def generate_pdf(user_data: Dict[str, Any], numerology_data: Dict[str, Any],
                interpretation_data: Dict[str, Any], report_type: str = 'full') -> Optional[str]:
    """
    Генерирует текстовый отчет (вместо PDF) и возвращает путь к файлу.
    Функция названа generate_pdf для совместимости с существующим кодом.
    """
    try:
        # Получаем директорию пользователя
        user_dir = get_user_directory(user_data)
        
        # Форматируем дату рождения
        birthdate_formatted = format_date(user_data.get('birthdate', ''))
        
        # Формируем имя файла для отчета
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_prefix = report_type
        filename = f"{file_prefix}_{timestamp}.txt"
        filepath = os.path.join(user_dir, filename)
        
        # Извлекаем данные интерпретации
        interp_data = extract_data_from_interpretation(interpretation_data)
        
        # Создаем текстовый отчет
        with open(filepath, 'w', encoding='utf-8') as f:
            # Заголовок
            f.write(f"{'=' * 50}\n")
            if report_type == 'compatibility':
                f.write("ОТЧЕТ О НУМЕРОЛОГИЧЕСКОЙ СОВМЕСТИМОСТИ\n")
            else:
                f.write("НУМЕРОЛОГИЧЕСКИЙ ОТЧЕТ\n")
            f.write(f"{'=' * 50}\n\n")
            
            # Информация о пользователе
            f.write(f"Отчет для: {user_data.get('fio', 'Пользователь')}\n")
            f.write(f"Дата рождения: {birthdate_formatted}\n")
            f.write(f"Дата составления: {datetime.now().strftime('%d.%m.%Y')}\n\n")
            
            # Введение
            f.write("ВВЕДЕНИЕ\n")
            f.write(f"{'-' * 40}\n")
            introduction = interp_data.get('introduction', '')
            if not introduction:
                introduction = "Персональный нумерологический анализ на основе ваших данных."
            f.write(f"{introduction}\n\n")
            
            # Ключевые числа
            f.write("КЛЮЧЕВЫЕ ЧИСЛА ВАШЕЙ СУДЬБЫ\n")
            f.write(f"{'-' * 40}\n")
            
            # Обработка различных чисел
            number_types = [
                ('life_path', 'Число жизненного пути'),
                ('expression', 'Число выражения'),
                ('soul_urge', 'Число души'),
                ('personality', 'Число личности')
            ]
            
            for num_key, num_name in number_types:
                num_value = numerology_data.get(num_key, '')
                interp_key = num_key.replace('soul_urge', 'soul') + '_interpretation'
                interp_text = interp_data.get(interp_key, f"Интерпретация {num_name.lower()}.")
                
                f.write(f"{num_name}: {num_value}\n")
                f.write(f"{interp_text}\n\n")
            
            # Подробный анализ
            f.write("ПОДРОБНЫЙ АНАЛИЗ ЧИСЕЛ\n")
            f.write(f"{'-' * 40}\n")
            
            for num_key, num_name in number_types:
                num_value = numerology_data.get(num_key, '')
                detailed_key = num_key.replace('soul_urge', 'soul') + '_detailed'
                detailed_text = interp_data.get(detailed_key, f"Подробный анализ {num_name.lower()}.")
                
                f.write(f"{num_name}: {num_value}\n")
                f.write(f"{detailed_text}\n\n")
            
            # Если это отчет о совместимости, добавляем соответствующую информацию
            if report_type == 'compatibility':
                f.write("АНАЛИЗ СОВМЕСТИМОСТИ\n")
                f.write(f"{'-' * 40}\n")
                
                # Информация о партнере
                if 'person2' in numerology_data:
                    partner_data = numerology_data.get('person2', {})
                    partner_name = partner_data.get('fio', 'Партнер')
                    birth_data = partner_data.get('birth_data', {})
                    partner_birthdate = birth_data.get('date', '') if isinstance(birth_data, dict) else ''
                    
                    f.write(f"Партнер: {partner_name}\n")
                    f.write(f"Дата рождения партнера: {format_date(partner_birthdate)}\n\n")
                
                # Данные совместимости
                compat_intro = interp_data.get('compatibility_intro', 'Анализ совместимости')
                f.write(f"{compat_intro}\n\n")
                
                # Числовая оценка совместимости
                score = interp_data.get('compatibility_score', '')
                if score == '':
                    # Пробуем получить из других источников
                    if 'compatibility' in numerology_data:
                        score = numerology_data.get('compatibility', {}).get('total', 0)
                        if isinstance(score, float):
                            score = int(score * 10)  # Преобразуем к проценту
                    else:
                        score = 0
                
                f.write(f"Общая совместимость: {score}%\n\n")
                
                # Сильные и слабые стороны
                f.write("Сильные стороны отношений:\n")
                strengths = interp_data.get('compatibility_strengths', 'Анализ сильных сторон отношений.')
                f.write(f"{strengths}\n\n")
                
                f.write("Возможные трудности:\n")
                challenges = interp_data.get('compatibility_challenges', 'Анализ возможных трудностей в отношениях.')
                f.write(f"{challenges}\n\n")
                
                f.write("Рекомендации по улучшению отношений:\n")
                recommendations = interp_data.get('compatibility_recommendations', 'Рекомендации для улучшения отношений.')
                f.write(f"{recommendations}\n\n")
            
            # Прогноз и рекомендации
            f.write("ПРОГНОЗ И РЕКОМЕНДАЦИИ\n")
            f.write(f"{'-' * 40}\n")
            
            forecast = interp_data.get('forecast', 'Прогноз на ближайшее время.')
            f.write(f"{forecast}\n\n")
            
            f.write("Личные рекомендации:\n")
            recommendations = interp_data.get('recommendations', 'Рекомендации для вашего развития.')
            f.write(f"{recommendations}\n\n")
            
            # Футер
            f.write(f"{'=' * 50}\n")
            f.write(f"© ИИ-Нумеролог {datetime.now().year}. Все права защищены.\n")
            f.write("Данный отчет сгенерирован с использованием искусственного интеллекта.\n")
            f.write("Для получения обновлений и еженедельных прогнозов подпишитесь в Telegram-боте.\n")
        
        logger.info(f"Отчет успешно сгенерирован: {filepath}")
        
        # Пытаемся также сгенерировать PDF с тем же именем (для совместимости)
        try:
            # Импортируем pdf_generator только здесь, чтобы избежать циклического импорта
            import importlib
            try:
                pdf_gen_module = importlib.import_module('pdf_generator')
                pdf_func = getattr(pdf_gen_module, 'generate_pdf')
                
                # Пытаемся сгенерировать PDF
                pdf_path = pdf_func(user_data, numerology_data, interpretation_data, report_type)
                if pdf_path:
                    logger.info(f"PDF также успешно сгенерирован: {pdf_path}")
                    return pdf_path
            except (ImportError, AttributeError) as e:
                logger.warning(f"Не удалось использовать pdf_generator: {e}")
            
            # Если PDF не сгенерирован, используем текстовый файл
            return filepath
            
        except Exception as pdf_error:
            logger.warning(f"Ошибка при генерации PDF: {pdf_error}")
            return filepath
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}")
        # В случае ошибки пытаемся создать файл в корневой директории
        emergency_path = os.path.join(REPORTS_PATH, f"emergency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(emergency_path, 'w', encoding='utf-8') as f:
                f.write(f"Отчет для: {user_data.get('fio', 'Пользователь')}\n")
                f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n")
                f.write("Произошла ошибка при создании полного отчета.\n")
                f.write(f"Нумерологические данные: {numerology_data}\n\n")
                
                # Пытаемся записать хотя бы базовую интерпретацию
                if isinstance(interpretation_data, dict):
                    for key, value in interpretation_data.items():
                        f.write(f"{key}: {value}\n")
                else:
                    f.write(f"Интерпретация: {interpretation_data}\n")
            
            logger.info(f"Создан аварийный отчет: {emergency_path}")
            return emergency_path
        except Exception as emergency_error:
            logger.error(f"Не удалось создать аварийный отчет: {emergency_error}")
            return None