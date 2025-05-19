"""
Простой генератор PDF-отчетов с использованием reportlab.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к директории для сохранения PDF
PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')

# Создаем директорию для хранения PDF, если она не существует
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов
    """
    for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        filename = filename.replace(char, '_')
    return filename.replace(' ', '_')

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

def format_date(date_value):
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

def generate_pdf(user_data: Dict[str, Any], numerology_data: Dict[str, Any],
                interpretation_data: Dict[str, Any], report_type: str = 'full') -> Optional[str]:
    """
    Генерирует PDF-отчет с использованием reportlab.
    В случае ошибки создает текстовый отчет как запасной вариант.
    
    Args:
        user_data: Данные пользователя
        numerology_data: Результаты нумерологических расчетов
        interpretation_data: Интерпретация от внешнего сервиса
        report_type: Тип отчета ('full' или 'compatibility')
        
    Returns:
        str: Путь к сгенерированному отчету или None в случае ошибки
    """
    try:
        # Получаем директорию пользователя
        user_dir = get_user_directory(user_data)
        
        # Форматируем дату рождения
        birthdate_formatted = format_date(user_data.get('birthdate', ''))
        
        # Формируем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = user_data.get('id', '1')
        file_prefix = f"{user_id}_{report_type}"
        
        # Пути к файлам
        pdf_path = os.path.join(user_dir, f"{file_prefix}_{timestamp}.pdf")
        txt_path = os.path.join(user_dir, f"{file_prefix}_{timestamp}.txt")
        
        try:
            # Генерируем PDF с использованием reportlab
            doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                                   rightMargin=2*cm, leftMargin=2*cm, 
                                   topMargin=2*cm, bottomMargin=2*cm)
            
            # Стили для содержимого
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            heading_style = styles['Heading1']
            subheading_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # Создаем элементы PDF
            story = []
            
            # Заголовок
            if report_type == 'compatibility':
                report_title = "Отчет о нумерологической совместимости"
            else:
                report_title = "Нумерологический отчет"
            story.append(Paragraph(report_title, title_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Информация о пользователе
            story.append(Paragraph(f"Отчет для: {user_data.get('fio', 'Пользователь')}", heading_style))
            story.append(Paragraph(f"Дата рождения: {birthdate_formatted}", normal_style))
            story.append(Paragraph(f"Дата составления: {datetime.now().strftime('%d.%m.%Y')}", normal_style))
            story.append(Spacer(1, 1*cm))
            
            # Получаем данные из интерпретации
            mini_report = None
            full_report = None
            
            if isinstance(interpretation_data, dict):
                mini_report = interpretation_data.get('mini_report')
                full_report = interpretation_data.get('full_report', {})
            else:
                mini_report = str(interpretation_data)
            
            # Введение
            introduction = ""
            if isinstance(full_report, dict) and 'introduction' in full_report:
                introduction = full_report['introduction']
            elif mini_report:
                introduction = mini_report
            else:
                introduction = "Персональный нумерологический анализ на основе ваших данных."
                
            story.append(Paragraph("Введение", heading_style))
            story.append(Paragraph(introduction, normal_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Ключевые числа и их интерпретации
            story.append(Paragraph("Ключевые числа вашей судьбы", heading_style))
            
            # Получаем значения чисел
            life_path = numerology_data.get('life_path', '')
            expression = numerology_data.get('expression', '')
            soul_urge = numerology_data.get('soul_urge', '')
            personality = numerology_data.get('personality', '')
            
            # Получаем интерпретации
            life_path_interp = ""
            expression_interp = ""
            soul_interp = ""
            personality_interp = ""
            
            if isinstance(full_report, dict):
                life_path_interp = full_report.get('life_path_interpretation', '')
                expression_interp = full_report.get('expression_interpretation', '')
                soul_interp = full_report.get('soul_interpretation', '')
                personality_interp = full_report.get('personality_interpretation', '')
            
            # Добавляем информацию о числах
            story.append(Paragraph(f"Число жизненного пути: {life_path}", subheading_style))
            story.append(Paragraph(life_path_interp or "Интерпретация числа жизненного пути.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph(f"Число выражения: {expression}", subheading_style))
            story.append(Paragraph(expression_interp or "Интерпретация числа выражения.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph(f"Число души: {soul_urge}", subheading_style))
            story.append(Paragraph(soul_interp or "Интерпретация числа души.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph(f"Число личности: {personality}", subheading_style))
            story.append(Paragraph(personality_interp or "Интерпретация числа личности.", normal_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Новая страница
            story.append(PageBreak())
            
            # Подробный анализ
            story.append(Paragraph("Подробный анализ чисел", heading_style))
            
            # Получаем подробные интерпретации
            life_path_detailed = ""
            expression_detailed = ""
            soul_detailed = ""
            personality_detailed = ""
            
            if isinstance(full_report, dict):
                life_path_detailed = full_report.get('life_path_detailed', '')
                expression_detailed = full_report.get('expression_detailed', '')
                soul_detailed = full_report.get('soul_detailed', '')
                personality_detailed = full_report.get('personality_detailed', '')
            
            # Добавляем подробные интерпретации
            story.append(Paragraph(f"Число жизненного пути: {life_path}", subheading_style))
            story.append(Paragraph(life_path_detailed or "Подробный анализ числа жизненного пути.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph(f"Число выражения: {expression}", subheading_style))
            story.append(Paragraph(expression_detailed or "Подробный анализ числа выражения.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph(f"Число души: {soul_urge}", subheading_style))
            story.append(Paragraph(soul_detailed or "Подробный анализ числа души.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph(f"Число личности: {personality}", subheading_style))
            story.append(Paragraph(personality_detailed or "Подробный анализ числа личности.", normal_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Для отчета о совместимости
            if report_type == 'compatibility':
                # Новая страница
                story.append(PageBreak())
                
                # Добавление информации о совместимости
                story.append(Paragraph("Анализ совместимости", heading_style))
                
                compatibility_report = interpretation_data.get('compatibility_report', {})
                
                if isinstance(compatibility_report, dict):
                    # Интро и оценка
                    compatibility_intro = compatibility_report.get('intro', '')
                    story.append(Paragraph(compatibility_intro or "Анализ совместимости между двумя людьми.", normal_style))
                    story.append(Spacer(1, 0.3*cm))
                    
                    compatibility_score = compatibility_report.get('score', 75)
                    story.append(Paragraph(f"Общая совместимость: {compatibility_score}%", subheading_style))
                    story.append(Spacer(1, 0.3*cm))
                    
                    # Сильные стороны
                    compatibility_strengths = compatibility_report.get('strengths', '')
                    story.append(Paragraph("Сильные стороны отношений", subheading_style))
                    story.append(Paragraph(compatibility_strengths or "Анализ сильных сторон отношений.", normal_style))
                    story.append(Spacer(1, 0.3*cm))
                    
                    # Трудности
                    compatibility_challenges = compatibility_report.get('challenges', '')
                    story.append(Paragraph("Возможные трудности", subheading_style))
                    story.append(Paragraph(compatibility_challenges or "Анализ возможных трудностей в отношениях.", normal_style))
                    story.append(Spacer(1, 0.3*cm))
                    
                    # Рекомендации
                    compatibility_recommendations = compatibility_report.get('recommendations', '')
                    story.append(Paragraph("Рекомендации", subheading_style))
                    story.append(Paragraph(compatibility_recommendations or "Рекомендации для улучшения отношений.", normal_style))
            
            # Новая страница
            story.append(PageBreak())
            
            # Прогноз и рекомендации
            story.append(Paragraph("Прогноз и рекомендации", heading_style))
            
            # Получаем прогноз и рекомендации
            forecast = ""
            recommendations = ""
            
            if isinstance(full_report, dict):
                forecast = full_report.get('forecast', '')
                recommendations = full_report.get('recommendations', '')
            
            # Добавляем прогноз и рекомендации
            story.append(Paragraph(forecast or "Прогноз на ближайшее время.", normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            story.append(Paragraph("Личные рекомендации", subheading_style))
            story.append(Paragraph(recommendations or "Рекомендации для вашего развития.", normal_style))
            
            # Футер
            story.append(Spacer(1, 1*cm))
            current_year = datetime.now().year
            footer_text = f"© ИИ-Нумеролог {current_year}. Все права защищены."
            story.append(Paragraph(footer_text, normal_style))
            story.append(Paragraph("Данный отчет сгенерирован с использованием искусственного интеллекта на основе нумерологических расчетов.", normal_style))
            story.append(Paragraph("Для получения обновлений и еженедельных прогнозов подпишитесь в Telegram-боте.", normal_style))
            
            # Собираем PDF
            doc.build(story)
            
            logger.info(f"PDF отчет успешно сгенерирован: {pdf_path}")
            
            # Также создаем текстовый отчет как резервную копию
            generate_text_report(user_data, numerology_data, interpretation_data, txt_path, report_type)
            
            return pdf_path
            
        except Exception as pdf_error:
            logger.error(f"Ошибка при генерации PDF: {pdf_error}")
            logger.warning("Создание текстового отчета вместо PDF")
            
            # Создаем текстовый отчет вместо PDF
            txt_path = generate_text_report(user_data, numerology_data, interpretation_data, txt_path, report_type)
            return txt_path
            
    except Exception as e:
        logger.error(f"Общая ошибка при генерации отчета: {e}")
        
        # В случае ошибки пытаемся создать простой текстовый отчет
        try:
            emergency_path = os.path.join(PDF_STORAGE_PATH, f"emergency_{timestamp}.txt")
            return generate_text_report(user_data, numerology_data, interpretation_data, emergency_path, report_type)
        except Exception as e2:
            logger.error(f"Не удалось создать даже аварийный отчет: {e2}")
            return None


def generate_text_report(user_data: Dict[str, Any], numerology_data: Dict[str, Any],
                       interpretation_data: Dict[str, Any], output_path: str, report_type: str = 'full') -> str:
    """
    Генерирует текстовый отчет на основе данных.
    
    Args:
        user_data: Данные пользователя
        numerology_data: Результаты нумерологических расчетов
        interpretation_data: Интерпретация от внешнего сервиса
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
            f.write(f"Отчет для: {user_data.get('fio', 'Пользователь')}\n")
            f.write(f"Дата рождения: {format_date(user_data.get('birthdate', ''))}\n")
            f.write(f"Дата составления: {datetime.now().strftime('%d.%m.%Y')}\n\n")
            
            # Получаем данные из интерпретации
            mini_report = None
            full_report = None
            
            if isinstance(interpretation_data, dict):
                mini_report = interpretation_data.get('mini_report')
                full_report = interpretation_data.get('full_report', {})
            else:
                mini_report = str(interpretation_data)
            
            # Введение
            introduction = ""
            if isinstance(full_report, dict) and 'introduction' in full_report:
                introduction = full_report['introduction']
            elif mini_report:
                introduction = mini_report
            else:
                introduction = "Персональный нумерологический анализ на основе ваших данных."
                
            f.write("ВВЕДЕНИЕ\n")
            f.write(f"{'-' * 40}\n")
            f.write(f"{introduction}\n\n")
            
            # Ключевые числа
            f.write("КЛЮЧЕВЫЕ ЧИСЛА ВАШЕЙ СУДЬБЫ\n")
            f.write(f"{'-' * 40}\n")
            
            # Получаем значения чисел
            life_path = numerology_data.get('life_path', '')
            expression = numerology_data.get('expression', '')
            soul_urge = numerology_data.get('soul_urge', '')
            personality = numerology_data.get('personality', '')
            
            # Получаем интерпретации
            life_path_interp = ""
            expression_interp = ""
            soul_interp = ""
            personality_interp = ""
            
            if isinstance(full_report, dict):
                life_path_interp = full_report.get('life_path_interpretation', '')
                expression_interp = full_report.get('expression_interpretation', '')
                soul_interp = full_report.get('soul_interpretation', '')
                personality_interp = full_report.get('personality_interpretation', '')
            
            # Добавляем информацию о числах
            f.write(f"Число жизненного пути: {life_path}\n")
            f.write(f"{life_path_interp or 'Интерпретация числа жизненного пути.'}\n\n")
            
            f.write(f"Число выражения: {expression}\n")
            f.write(f"{expression_interp or 'Интерпретация числа выражения.'}\n\n")
            
            f.write(f"Число души: {soul_urge}\n")
            f.write(f"{soul_interp or 'Интерпретация числа души.'}\n\n")
            
            f.write(f"Число личности: {personality}\n")
            f.write(f"{personality_interp or 'Интерпретация числа личности.'}\n\n")
            
            # Подробный анализ
            f.write("ПОДРОБНЫЙ АНАЛИЗ ЧИСЕЛ\n")
            f.write(f"{'-' * 40}\n")
            
            # Получаем подробные интерпретации
            life_path_detailed = ""
            expression_detailed = ""
            soul_detailed = ""
            personality_detailed = ""
            
            if isinstance(full_report, dict):
                life_path_detailed = full_report.get('life_path_detailed', '')
                expression_detailed = full_report.get('expression_detailed', '')
                soul_detailed = full_report.get('soul_detailed', '')
                personality_detailed = full_report.get('personality_detailed', '')
            
            # Добавляем подробные интерпретации
            f.write(f"Число жизненного пути: {life_path}\n")
            f.write(f"{life_path_detailed or 'Подробный анализ числа жизненного пути.'}\n\n")
            
            f.write(f"Число выражения: {expression}\n")
            f.write(f"{expression_detailed or 'Подробный анализ числа выражения.'}\n\n")
            
            f.write(f"Число души: {soul_urge}\n")
            f.write(f"{soul_detailed or 'Подробный анализ числа души.'}\n\n")
            
            f.write(f"Число личности: {personality}\n")
            f.write(f"{personality_detailed or 'Подробный анализ числа личности.'}\n\n")
            
            # Для отчета о совместимости
            if report_type == 'compatibility':
                # Добавление информации о совместимости
                f.write("АНАЛИЗ СОВМЕСТИМОСТИ\n")
                f.write(f"{'-' * 40}\n")
                
                compatibility_report = interpretation_data.get('compatibility_report', {})
                
                if isinstance(compatibility_report, dict):
                    # Интро и оценка
                    compatibility_intro = compatibility_report.get('intro', '')
                    f.write(f"{compatibility_intro or 'Анализ совместимости между двумя людьми.'}\n\n")
                    
                    compatibility_score = compatibility_report.get('score', 75)
                    f.write(f"Общая совместимость: {compatibility_score}%\n\n")
                    
                    # Сильные стороны
                    compatibility_strengths = compatibility_report.get('strengths', '')
                    f.write("Сильные стороны отношений:\n")
                    f.write(f"{compatibility_strengths or 'Анализ сильных сторон отношений.'}\n\n")
                    
                    # Трудности
                    compatibility_challenges = compatibility_report.get('challenges', '')
                    f.write("Возможные трудности:\n")
                    f.write(f"{compatibility_challenges or 'Анализ возможных трудностей в отношениях.'}\n\n")
                    
                    # Рекомендации
                    compatibility_recommendations = compatibility_report.get('recommendations', '')
                    f.write("Рекомендации:\n")
                    f.write(f"{compatibility_recommendations or 'Рекомендации для улучшения отношений.'}\n\n")
            
            # Прогноз и рекомендации
            f.write("ПРОГНОЗ И РЕКОМЕНДАЦИИ\n")
            f.write(f"{'-' * 40}\n")
            
            # Получаем прогноз и рекомендации
            forecast = ""
            recommendations = ""
            
            if isinstance(full_report, dict):
                forecast = full_report.get('forecast', '')
                recommendations = full_report.get('recommendations', '')
            
            # Добавляем прогноз и рекомендации
            f.write(f"{forecast or 'Прогноз на ближайшее время.'}\n\n")
            
            f.write("Личные рекомендации:\n")
            f.write(f"{recommendations or 'Рекомендации для вашего развития.'}\n\n")
            
            # Футер
            f.write(f"{'=' * 50}\n")
            current_year = datetime.now().year
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
                f.write(f"Пользователь: {user_data.get('fio', 'Неизвестный')}\n")
                f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n")
                f.write("Текст отчета не удалось отформатировать.\n")
            return simple_path
        except:
            # Если все не получилось, возвращаем исходный путь даже без файла
            return output_path