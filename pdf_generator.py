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

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация шрифта с поддержкой кириллицы
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    FONT_NAME = 'DejaVuSans'
except:
    # Если шрифт не найден, используем стандартный
    FONT_NAME = 'Helvetica'
    logger.warning("Шрифт DejaVuSans не найден, используется Helvetica (без поддержки кириллицы)")

# И при создании стилей
normal_style = ParagraphStyle(name='Normal', fontName=FONT_NAME, fontSize=10)
title_style = ParagraphStyle(name='Title', fontName=FONT_NAME, fontSize=18, alignment=1)
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

def get_jinja_template():
    """
    Получает объект шаблона Jinja2 для генерации HTML.
    
    Returns:
        jinja2.Template: Объект шаблона Jinja2
    """
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    try:
        template = template_env.get_template(TEMPLATE_FILE)
        return template
    except jinja2.exceptions.TemplateNotFound:
        logger.error(f"Шаблон {TEMPLATE_FILE} не найден")
        # Создаем базовый шаблон, если основной не найден
        basic_template = """
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
                <h2>Прогноз и рекомендации</h2>
                <p>{{ forecast }}</p>
                <p>{{ recommendations }}</p>
            </div>
            
            <footer>
                <p>© ИИ-Нумеролог {{ current_year }}. Все права защищены.</p>
            </footer>
        </body>
        </html>
        """
        # Создаем временный шаблон в файле
        with open("temp_template.html", "w", encoding="utf-8") as temp_file:
            temp_file.write(basic_template)
        return template_env.get_template("temp_template.html")


def generate_pdf(user_data: Dict[str, Any], numerology_data: Dict[str, Any], 
                interpretation_data: Dict[str, Any], report_type: str = 'full') -> Optional[str]:
    """
    Генерирует PDF-отчет на основе шаблона и данных.
    
    Args:
        user_data: Данные пользователя (ФИО, дата рождения и т.д.)
        numerology_data: Результаты нумерологических расчетов
        interpretation_data: Интерпретация результатов от ИИ
        report_type: Тип отчета ('full' или 'compatibility')
        
    Returns:
        str: Путь к сгенерированному PDF-файлу или None в случае ошибки
    """
    try:
        # Получаем директорию пользователя
        user_dir = get_user_directory(user_data)
        
        # Форматируем дату рождения
        birthdate_formatted = format_date(user_data.get('birthdate', ''))
        
        # Подготавливаем данные для шаблона
        template_data = prepare_template_data(user_data, numerology_data, interpretation_data, birthdate_formatted, report_type)
        
        # Получаем шаблон
        template = get_jinja_template()
        
        # Формируем имя файла для PDF и текстового отчета
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_prefix = f"{report_type}"
        pdf_filename = f"{file_prefix}_{timestamp}.pdf"
        txt_filename = f"{file_prefix}_{timestamp}.txt"
        
        pdf_path = os.path.join(user_dir, pdf_filename)
        txt_path = os.path.join(user_dir, txt_filename)
        
        # Генерируем HTML на основе шаблона
        html_content = template.render(**template_data)
        
        # Сначала сохраняем HTML во временный файл (для отладки)
        temp_html_path = os.path.join(user_dir, f"{file_prefix}_{timestamp}.html")
        with open(temp_html_path, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)
        
        try:
            # Генерируем PDF
            HTML(string=html_content).write_pdf(pdf_path)
            logger.info(f"PDF отчет успешно сгенерирован: {pdf_path}")
        except Exception as pdf_error:
            logger.error(f"Ошибка при генерации PDF: {pdf_error}")
            logger.info("Пробуем альтернативный способ генерации PDF...")
            try:
                # Альтернативный способ без weasyprint - создаем только текстовый отчет
                generate_text_report(template_data, txt_path, report_type)
                return txt_path
            except Exception as txt_error:
                logger.error(f"Ошибка при генерации текстового отчета: {txt_error}")
                return None
        
        # Генерируем также текстовый отчет как резервную копию
        generate_text_report(template_data, txt_path, report_type)
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"Общая ошибка при генерации отчета: {e}")
        return None


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


def prepare_template_data(user_data: Dict[str, Any], numerology_data: Dict[str, Any], 
                         interpretation_data: Dict[str, Any], birthdate_formatted: str, 
                         report_type: str) -> Dict[str, Any]:
    """
    Подготавливает данные для шаблона.
    """
    # Базовые данные
    template_data = {
        'user_name': user_data.get('fio', 'Пользователь'),
        'birthdate': birthdate_formatted,
        'current_date': datetime.now().strftime('%d.%m.%Y'),
        'current_year': datetime.now().year,
    }
    
    # Добавляем нумерологические данные
    for key in ['life_path', 'expression', 'soul_urge', 'personality', 'destiny']:
        template_key = key.replace('soul_urge', 'soul')
        template_data[f'{template_key}_number'] = numerology_data.get(key, '')
    
    # Добавляем интерпретации
    # Проверяем, является ли interpretation_data словарем
    if isinstance(interpretation_data, dict):
        # Если у нас полноценный JSON ответ
        intro_text = interpretation_data.get('introduction', '')
        if not intro_text and isinstance(interpretation_data.get('full_report'), dict):
            intro_text = interpretation_data.get('full_report', {}).get('introduction', '')
        template_data['introduction'] = intro_text or "Персональный нумерологический анализ на основе ваших данных."
        
        # Добавляем интерпретации для каждого числа
        for num_type in ['life_path', 'expression', 'soul', 'personality']:
            interp_key = f'{num_type}_interpretation'
            detailed_key = f'{num_type}_detailed'
            
            # Проверяем разные источники данных
            interp_value = interpretation_data.get(interp_key, '')
            if not interp_value and isinstance(interpretation_data.get('full_report'), dict):
                interp_value = interpretation_data.get('full_report', {}).get(interp_key, '')
            
            detailed_value = interpretation_data.get(detailed_key, '')
            if not detailed_value and isinstance(interpretation_data.get('full_report'), dict):
                detailed_value = interpretation_data.get('full_report', {}).get(detailed_key, '')
            
            # Добавляем в данные шаблона
            template_data[interp_key] = interp_value or f"Интерпретация числа {num_type.replace('_', ' ')}."
            template_data[detailed_key] = detailed_value or f"Подробный анализ числа {num_type.replace('_', ' ')}."
        
        # Добавляем прогноз и рекомендации
        forecast = interpretation_data.get('forecast', '')
        if not forecast and isinstance(interpretation_data.get('full_report'), dict):
            forecast = interpretation_data.get('full_report', {}).get('forecast', '')
        template_data['forecast'] = forecast or "Прогноз на ближайшее время."
        
        recommendations = interpretation_data.get('recommendations', '')
        if not recommendations and isinstance(interpretation_data.get('full_report'), dict):
            recommendations = interpretation_data.get('full_report', {}).get('recommendations', '')
        template_data['recommendations'] = recommendations or "Рекомендации для вашего развития."
        
        # Для отчета о совместимости
        if report_type == 'compatibility':
            compat_data = interpretation_data.get('compatibility_report', {})
            if not compat_data:
                compat_data = interpretation_data.get('compatibility', {})
            
            template_data['compatibility_report'] = True
            template_data['compatibility_intro'] = compat_data.get('intro', 'Анализ совместимости')
            template_data['compatibility_score'] = compat_data.get('score', 75)
            template_data['compatibility_strengths'] = compat_data.get('strengths', 'Сильные стороны отношений')
            template_data['compatibility_challenges'] = compat_data.get('challenges', 'Возможные трудности')
            template_data['compatibility_recommendations'] = compat_data.get('recommendations', 'Рекомендации')
            
            # Добавляем информацию о партнере
            if 'person2' in numerology_data:
                partner_data = numerology_data.get('person2', {})
                template_data['partner_name'] = partner_data.get('fio', 'Партнер')
                birth_data = partner_data.get('birth_data', {})
                partner_birthdate = birth_data.get('date', '') if isinstance(birth_data, dict) else ''
                template_data['partner_birthdate'] = format_date(partner_birthdate)
        else:
            template_data['compatibility_report'] = False
    else:
        # Если interpretation_data не словарь, используем его как текст
        template_data['introduction'] = str(interpretation_data) or "Персональный нумерологический анализ."
        
        # Заполняем стандартные поля
        for num_type in ['life_path', 'expression', 'soul', 'personality']:
            template_data[f'{num_type}_interpretation'] = f"Интерпретация числа {num_type.replace('_', ' ')}."
            template_data[f'{num_type}_detailed'] = f"Подробный анализ числа {num_type.replace('_', ' ')}."
        
        template_data['forecast'] = "Прогноз на ближайшее время."
        template_data['recommendations'] = "Рекомендации для вашего развития."
    
    return template_data


def generate_text_report(template_data: Dict[str, Any], txt_path: str, report_type: str = 'full'):
    """
    Генерирует текстовый отчет на основе данных шаблона.
    """
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            # Заголовок
            f.write(f"{'=' * 50}\n")
            if report_type == 'compatibility':
                f.write("ОТЧЕТ О НУМЕРОЛОГИЧЕСКОЙ СОВМЕСТИМОСТИ\n")
            else:
                f.write("НУМЕРОЛОГИЧЕСКИЙ ОТЧЕТ\n")
            f.write(f"{'=' * 50}\n\n")
            
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
            if template_data.get('compatibility_report', False):
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
        
        logger.info(f"Текстовый отчет успешно сгенерирован: {txt_path}")
        return txt_path
    except Exception as e:
        logger.error(f"Ошибка при генерации текстового отчета: {e}")
        return None