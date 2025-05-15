# pdf_generator_improved.py
"""
Улучшенный модуль для генерации PDF и текстовых отчетов.
Решает проблемы с форматированием и добавляет структурированное хранение отчетов.
"""

import os
import logging
import shutil
from datetime import datetime
import re
from typing import Dict, Any, Optional, Union
import jinja2
from weasyprint import HTML, CSS

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к HTML-шаблону и директории для сохранения отчетов
TEMPLATE_FILE = 'pdf_template.html'
PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')

# Создаем директорию для хранения отчетов, если она не существует
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

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
    user_dir = os.path.join(PDF_STORAGE_PATH, sanitized_name)
    
    # Создаем директорию, если она не существует
    os.makedirs(user_dir, exist_ok=True)
    
    return user_dir

def create_basic_html_template() -> str:
    """
    Создает базовый HTML-шаблон для отчета
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Нумерологический отчет</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #4b0082; text-align: center; }
            h2 { color: #4b0082; border-bottom: 1px solid #ddd; }
            .number { font-size: 24px; font-weight: bold; color: #4b0082; }
            .section { margin: 20px 0; }
            footer { margin-top: 50px; text-align: center; font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <h1>Нумерологический отчет для {{ user_name }}</h1>
        <p>Дата рождения: {{ birthdate }}</p>
        <p>Дата составления: {{ current_date }}</p>
        
        <div class="section">
            <h2>Ключевые числа вашей судьбы</h2>
            <p><span class="number">{{ life_path_number }}</span> - Число жизненного пути<br>{{ life_path_interpretation }}</p>
            <p><span class="number">{{ expression_number }}</span> - Число выражения<br>{{ expression_interpretation }}</p>
            <p><span class="number">{{ soul_number }}</span> - Число души<br>{{ soul_interpretation }}</p>
            <p><span class="number">{{ personality_number }}</span> - Число личности<br>{{ personality_interpretation }}</p>
        </div>
        
        <div class="section">
            <h2>Подробный анализ</h2>
            <h3>Число жизненного пути: {{ life_path_number }}</h3>
            <p>{{ life_path_detailed }}</p>
            
            <h3>Число выражения: {{ expression_number }}</h3>
            <p>{{ expression_detailed }}</p>
            
            <h3>Число души: {{ soul_number }}</h3>
            <p>{{ soul_detailed }}</p>
            
            <h3>Число личности: {{ personality_number }}</h3>
            <p>{{ personality_detailed }}</p>
        </div>
        
        <div class="section">
            <h2>Прогноз и рекомендации</h2>
            <p>{{ forecast }}</p>
            <p><strong>Рекомендации:</strong> {{ recommendations }}</p>
        </div>
        
        <footer>
            <p>© ИИ-Нумеролог {{ current_year }}. Все права защищены.</p>
        </footer>
    </body>
    </html>
    """

def get_jinja_template():
    """
    Получает объект шаблона Jinja2 для генерации HTML
    """
    try:
        # Попытка загрузить шаблон из файла
        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader)
        
        # Проверяем существование файла шаблона
        if os.path.exists(TEMPLATE_FILE):
            template = template_env.get_template(TEMPLATE_FILE)
            logger.info(f"Шаблон {TEMPLATE_FILE} успешно загружен")
            return template
        else:
            logger.warning(f"Шаблон {TEMPLATE_FILE} не найден, используем базовый шаблон")
            
            # Создаем временный файл с базовым шаблоном
            basic_template = create_basic_html_template()
            temp_template_file = "temp_template.html"
            
            with open(temp_template_file, "w", encoding="utf-8") as f:
                f.write(basic_template)
                
            template = template_env.get_template(temp_template_file)
            return template
    except Exception as e:
        logger.error(f"Ошибка при загрузке шаблона: {e}")
        
        # Создаем шаблон из строки при ошибке
        basic_template = create_basic_html_template()
        return jinja2.Template(basic_template)

def format_date(date_value: Union[str, datetime.date]) -> str:
    """
    Форматирует дату в читаемый формат
    """
    if isinstance(date_value, str):
        try:
            # Пробуем разные форматы даты
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

def prepare_template_data(user_data: Dict[str, Any], numerology_data: Dict[str, Any], 
                         interpretation_data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Подготавливает данные для шаблона
    """
    # Форматируем дату рождения
    birthdate_formatted = format_date(user_data.get('birthdate', ''))
    
    # Базовые данные
    template_data = {
        'user_name': user_data.get('fio', 'Пользователь'),
        'birthdate': birthdate_formatted,
        'current_date': datetime.now().strftime('%d.%m.%Y'),
        'current_year': datetime.now().year,
    }
    
    # Добавляем нумерологические данные
    for key in ['life_path', 'expression', 'soul_urge', 'personality', 'destiny']:
        if key in numerology_data:
            template_key = key.replace('soul_urge', 'soul')
            template_data[f'{template_key}_number'] = numerology_data.get(key, '')
    
    # Добавляем интерпретации
    # Проверяем формат interpretation_data
    if isinstance(interpretation_data, dict):
        # Если у нас есть полноценный JSON-ответ
        
        # Обрабатываем full_report
        full_report = interpretation_data.get('full_report', {})
        if isinstance(full_report, dict):
            # Копируем все поля из full_report в template_data
            for key, value in full_report.items():
                template_data[key] = value
        
        # Если есть мини-отчет, добавляем его содержимое в introduction
        if 'mini_report' in interpretation_data:
            template_data['introduction'] = interpretation_data['mini_report']
        
        # Для совместимости
        if report_type == 'compatibility':
            compatibility_report = interpretation_data.get('compatibility_report', {})
            if isinstance(compatibility_report, dict):
                template_data['compatibility_report'] = True
                for key, value in compatibility_report.items():
                    template_data[f'compatibility_{key}'] = value
            
            # Добавляем информацию о партнере, если есть
            if 'person2' in numerology_data:
                person2 = numerology_data.get('person2', {})
                template_data['partner_name'] = person2.get('fio', 'Партнер')
                birth_data = person2.get('birth_data', {})
                partner_birthdate = birth_data.get('date', '') if isinstance(birth_data, dict) else ''
                template_data['partner_birthdate'] = format_date(partner_birthdate)
    else:
        # Если interpretation_data не словарь, преобразуем в строку
        interpretation_text = str(interpretation_data)
        template_data['introduction'] = interpretation_text
    
    # Заполнение недостающих полей значениями по умолчанию
    default_fields = {
        'introduction': 'Ваш персональный нумерологический анализ.',
        'life_path_interpretation': 'Интерпретация числа жизненного пути.',
        'expression_interpretation': 'Интерпретация числа выражения.',
        'soul_interpretation': 'Интерпретация числа души.',
        'personality_interpretation': 'Интерпретация числа личности.',
        'life_path_detailed': 'Подробный анализ числа жизненного пути.',
        'expression_detailed': 'Подробный анализ числа выражения.',
        'soul_detailed': 'Подробный анализ числа души.',
        'personality_detailed': 'Подробный анализ числа личности.',
        'forecast': 'Прогноз на ближайшее время.',
        'recommendations': 'Рекомендации для вашего развития.'
    }
    
    for field, default_value in default_fields.items():
        if field not in template_data or not template_data[field]:
            template_data[field] = default_value
    
    return template_data

def generate_pdf(user_data: Dict[str, Any], numerology_data: Dict[str, Any], 
                interpretation_data: Dict[str, Any], report_type: str = 'full') -> Optional[str]:
    """
    Генерирует PDF-отчет на основе шаблона и данных
    В случае ошибки создает текстовый отчет как запасной вариант
    
    Args:
        user_data: Данные пользователя
        numerology_data: Результаты нумерологических расчетов
        interpretation_data: Интерпретация от внешнего сервиса
        report_type: Тип отчета ('full' или 'compatibility')
        
    Returns:
        str: Путь к сгенерированному файлу отчета
    """
    try:
        # Получаем директорию пользователя
        user_dir = get_user_directory(user_data)
        
        # Подготавливаем данные для шаблона
        template_data = prepare_template_data(user_data, numerology_data, interpretation_data, report_type)
        
        # Получаем шаблон
        template = get_jinja_template()
        
        # Формируем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = user_data.get('id', '1')
        file_prefix = f"{user_id}_{report_type}"
        
        # Пути к файлам
        pdf_path = os.path.join(user_dir, f"{file_prefix}_{timestamp}.pdf")
        html_path = os.path.join(user_dir, f"{file_prefix}_{timestamp}.html")
        txt_path = os.path.join(user_dir, f"{file_prefix}_{timestamp}.txt")
        
        # Генерируем HTML
        html_content = template.render(**template_data)
        
        # Сохраняем HTML во временный файл
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            logger.info(f"HTML отчет сохранен: {html_path}")
        
        try:
            # Генерируем PDF
            HTML(string=html_content).write_pdf(pdf_path)
            logger.info(f"PDF отчет успешно сгенерирован: {pdf_path}")
            
            # Также создаем текстовый отчет как резервную копию
            generate_text_report(template_data, txt_path, report_type)
            
            return pdf_path
        except Exception as pdf_error:
            logger.error(f"Ошибка при генерации PDF: {pdf_error}")
            logger.warning("Создание текстового отчета вместо PDF")
            
            # Создаем текстовый отчет вместо PDF
            txt_path = generate_text_report(template_data, txt_path, report_type)
            return txt_path
            
    except Exception as e:
        logger.error(f"Общая ошибка при генерации отчета: {e}")
        
        # Аварийное создание простого текстового отчета
        try:
            emergency_path = os.path.join(PDF_STORAGE_PATH, f"emergency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(emergency_path, 'w', encoding='utf-8') as f:
                f.write(f"Нумерологический отчет\n")
                f.write(f"====================\n\n")
                f.write(f"Имя: {user_data.get('fio', 'Пользователь')}\n")
                f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n")
                
                # Записываем доступные данные
                if isinstance(interpretation_data, dict):
                    for key, value in interpretation_data.items():
                        if isinstance(value, str):
                            f.write(f"{key}: {value}\n\n")
                        elif isinstance(value, dict):
                            f.write(f"{key}:\n")
                            for k, v in value.items():
                                if isinstance(v, str):
                                    f.write(f"  {k}: {v}\n")
                            f.write("\n")
                else:
                    f.write(f"Интерпретация: {interpretation_data}\n\n")
                
                f.write(f"\nПримечание: Этот аварийный отчет создан из-за ошибки при генерации полного отчета.\n")
            
            logger.info(f"Создан аварийный отчет: {emergency_path}")
            return emergency_path
        except Exception as emergency_error:
            logger.error(f"Не удалось создать аварийный отчет: {emergency_error}")
            return None


def generate_text_report(template_data: Dict[str, Any], output_path: str, report_type: str = 'full') -> str:
    """
    Генерирует текстовый отчет на основе данных шаблона
    
    Args:
        template_data: Данные для шаблона
        output_path: Путь к выходному файлу
        report_type: Тип отчета ('full' или 'compatibility')
        
    Returns:
        str: Путь к сгенерированному текстовому отчету
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Заголовок
            f.write("==================================================\n")
            if report_type == 'compatibility':
                f.write("ОТЧЕТ О НУМЕРОЛОГИЧЕСКОЙ СОВМЕСТИМОСТИ\n")
            else:
                f.write("НУМЕРОЛОГИЧЕСКИЙ ОТЧЕТ\n")
            f.write("==================================================\n\n")
            
            # Информация о пользователе
            f.write(f"Отчет для: {template_data.get('user_name', 'Пользователь')}\n")
            f.write(f"Дата рождения: {template_data.get('birthdate', '')}\n")
            f.write(f"Дата составления: {template_data.get('current_date', '')}\n\n")
            
            # Введение
            f.write("ВВЕДЕНИЕ\n")
            f.write(f"{'-' * 40}\n")
            f.write(f"{template_data.get('introduction', '')}\n\n")
            
            # Ключевые числа
            f.write("КЛЮЧЕВЫЕ ЧИСЛА ВАШЕЙ СУДЬБЫ\n")
            f.write(f"{'-' * 40}\n")
            
            # Число жизненного пути
            lp = template_data.get('life_path_number', '')
            f.write(f"Число жизненного пути: {lp}\n")
            f.write(f"{template_data.get('life_path_interpretation', '')}\n\n")
            
            # Число выражения
            exp = template_data.get('expression_number', '')
            f.write(f"Число выражения: {exp}\n")
            f.write(f"{template_data.get('expression_interpretation', '')}\n\n")
            
            # Число души
            soul = template_data.get('soul_number', '')
            f.write(f"Число души: {soul}\n")
            f.write(f"{template_data.get('soul_interpretation', '')}\n\n")
            
            # Число личности
            pers = template_data.get('personality_number', '')
            f.write(f"Число личности: {pers}\n")
            f.write(f"{template_data.get('personality_interpretation', '')}\n\n")
            
            # Подробный анализ
            f.write("ПОДРОБНЫЙ АНАЛИЗ ЧИСЕЛ\n")
            f.write(f"{'-' * 40}\n")
            
            f.write(f"Число жизненного пути: {lp}\n")
            f.write(f"{template_data.get('life_path_detailed', '')}\n\n")
            
            f.write(f"Число выражения: {exp}\n")
            f.write(f"{template_data.get('expression_detailed', '')}\n\n")
            
            f.write(f"Число души: {soul}\n")
            f.write(f"{template_data.get('soul_detailed', '')}\n\n")
            
            f.write(f"Число личности: {pers}\n")
            f.write(f"{template_data.get('personality_detailed', '')}\n\n")
            
            # Дополнительная информация для отчета о совместимости
            if report_type == 'compatibility' or template_data.get('compatibility_report', False):
                f.write("АНАЛИЗ СОВМЕСТИМОСТИ\n")
                f.write(f"{'-' * 40}\n")
                
                if 'partner_name' in template_data:
                    f.write(f"Партнер: {template_data.get('partner_name', '')}\n")
                if 'partner_birthdate' in template_data:
                    f.write(f"Дата рождения партнера: {template_data.get('partner_birthdate', '')}\n\n")
                
                f.write(f"{template_data.get('compatibility_intro', '')}\n\n")
                
                score = template_data.get('compatibility_score', 0)
                f.write(f"Общая совместимость: {score}%\n\n")
                
                f.write("Сильные стороны отношений:\n")
                f.write(f"{template_data.get('compatibility_strengths', '')}\n\n")
                
                f.write("Возможные трудности:\n")
                f.write(f"{template_data.get('compatibility_challenges', '')}\n\n")
                
                f.write("Рекомендации:\n")
                f.write(f"{template_data.get('compatibility_recommendations', '')}\n\n")
            
            # Прогноз и рекомендации
            f.write("ПРОГНОЗ И РЕКОМЕНДАЦИИ\n")
            f.write(f"{'-' * 40}\n")
            
            f.write(f"{template_data.get('forecast', '')}\n\n")
            
            f.write("Личные рекомендации:\n")
            f.write(f"{template_data.get('recommendations', '')}\n\n")
            
            # Футер
            f.write(f"{'=' * 50}\n")
            current_year = template_data.get('current_year', datetime.now().year)
            f.write(f"© ИИ-Нумеролог {current_year}. Все права защищены.\n")
            f.write("Данный отчет сгенерирован с использованием искусственного интеллекта.\n")
            f.write("Для получения обновлений и еженедельных прогнозов подпишитесь в Telegram-боте.\n")
        
        logger.info(f"Текстовый отчет успешно сгенерирован: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Ошибка при генерации текстового отчета: {e}")
        
        # В случае ошибки пытаемся создать очень простой отчет
        try:
            simple_path = output_path.replace('.txt', '_simple.txt')
            with open(simple_path, 'w', encoding='utf-8') as f:
                f.write("НУМЕРОЛОГИЧЕСКИЙ ОТЧЕТ\n\n")
                f.write(f"Пользователь: {template_data.get('user_name', 'Неизвестный')}\n")
                f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n")
                f.write("Текст отчета не удалось отформатировать.\n")
            return simple_path
        except:
            return None