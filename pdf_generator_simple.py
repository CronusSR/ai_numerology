"""
Упрощенная версия модуля для генерации PDF-отчетов с использованием reportlab.
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

def generate_pdf(user_data: Dict[str, Any], numerology_data: Dict[str, Any],
                interpretation_data: Dict[str, Any], report_type: str = 'full') -> Optional[str]:
    """
    Генерирует PDF-отчет с использованием reportlab.
    
    Args:
        user_data: Данные пользователя (ФИО, дата рождения и т.д.)
        numerology_data: Результаты нумерологических расчетов
        interpretation_data: Интерпретация результатов от ИИ
        report_type: Тип отчета ('full' или 'compatibility')
        
    Returns:
        str: Путь к сгенерированному PDF-файлу или None в случае ошибки
    """
    try:
        # Форматируем дату рождения, если она представлена строкой
        if isinstance(user_data.get('birthdate'), str):
            try:
                birthdate = datetime.strptime(user_data['birthdate'], "%Y-%m-%d").date()
                birthdate_formatted = birthdate.strftime('%d.%m.%Y')
            except (ValueError, TypeError):
                birthdate_formatted = user_data.get('birthdate', '')
        else:
            birthdate_formatted = user_data.get('birthdate', '').strftime('%d.%m.%Y') if user_data.get('birthdate') else ''
        
        # Формируем имя файла для PDF
        user_id = user_data.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"{user_id}_{report_type}_{timestamp}.pdf"
        pdf_path = os.path.join(PDF_STORAGE_PATH, pdf_filename)
        
        # Создаем объект PDF
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
        report_title = "Нумерологический отчет" if report_type == 'full' else "Отчет о нумерологической совместимости"
        story.append(Paragraph(report_title, title_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Информация о пользователе
        story.append(Paragraph(f"Отчет для: {user_data.get('fio', 'Пользователь')}", heading_style))
        story.append(Paragraph(f"Дата рождения: {birthdate_formatted}", normal_style))
        story.append(Paragraph(f"Дата составления: {datetime.now().strftime('%d.%m.%Y')}", normal_style))
        story.append(Spacer(1, 1*cm))
        
        # Введение
        introduction = interpretation_data.get('introduction', 'Нумерологический анализ на основе ваших персональных данных.')
        story.append(Paragraph("Введение", heading_style))
        story.append(Paragraph(introduction, normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Ключевые числа
        story.append(Paragraph("Ключевые числа вашей судьбы", heading_style))
        
        # Число жизненного пути
        life_path = numerology_data.get('life_path', '')
        life_path_interpretation = interpretation_data.get('life_path_interpretation', '')
        
        story.append(Paragraph(f"Число жизненного пути: {life_path}", subheading_style))
        story.append(Paragraph(life_path_interpretation, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Число выражения
        expression = numerology_data.get('expression', '')
        expression_interpretation = interpretation_data.get('expression_interpretation', '')
        
        story.append(Paragraph(f"Число выражения: {expression}", subheading_style))
        story.append(Paragraph(expression_interpretation, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Число души
        soul_urge = numerology_data.get('soul_urge', '')
        soul_interpretation = interpretation_data.get('soul_interpretation', '')
        
        story.append(Paragraph(f"Число души: {soul_urge}", subheading_style))
        story.append(Paragraph(soul_interpretation, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Число личности
        personality = numerology_data.get('personality', '')
        personality_interpretation = interpretation_data.get('personality_interpretation', '')
        
        story.append(Paragraph(f"Число личности: {personality}", subheading_style))
        story.append(Paragraph(personality_interpretation, normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Новая страница
        story.append(PageBreak())
        
        # Подробный анализ
        story.append(Paragraph("Подробный анализ чисел", heading_style))
        
        # Подробное описание числа жизненного пути
        life_path_detailed = interpretation_data.get('life_path_detailed', '')
        story.append(Paragraph(f"Число жизненного пути: {life_path}", subheading_style))
        story.append(Paragraph(life_path_detailed, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Подробное описание числа выражения
        expression_detailed = interpretation_data.get('expression_detailed', '')
        story.append(Paragraph(f"Число выражения: {expression}", subheading_style))
        story.append(Paragraph(expression_detailed, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Подробное описание числа души
        soul_detailed = interpretation_data.get('soul_detailed', '')
        story.append(Paragraph(f"Число души: {soul_urge}", subheading_style))
        story.append(Paragraph(soul_detailed, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Подробное описание числа личности
        personality_detailed = interpretation_data.get('personality_detailed', '')
        story.append(Paragraph(f"Число личности: {personality}", subheading_style))
        story.append(Paragraph(personality_detailed, normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Если это отчет о совместимости, добавляем соответствующие данные
        if report_type == 'compatibility':
            # Новая страница
            story.append(PageBreak())
            
            # Анализ совместимости
            story.append(Paragraph("Анализ совместимости", heading_style))
            
            compatibility_intro = interpretation_data.get('intro', '')
            story.append(Paragraph(compatibility_intro, normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Совместимость (в процентах)
            compatibility_score = interpretation_data.get('score', 0)
            story.append(Paragraph(f"Общая совместимость: {compatibility_score}%", subheading_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Сильные стороны
            compatibility_strengths = interpretation_data.get('strengths', '')
            story.append(Paragraph("Сильные стороны отношений", subheading_style))
            story.append(Paragraph(compatibility_strengths, normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Возможные трудности
            compatibility_challenges = interpretation_data.get('challenges', '')
            story.append(Paragraph("Возможные трудности", subheading_style))
            story.append(Paragraph(compatibility_challenges, normal_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Рекомендации
            compatibility_recommendations = interpretation_data.get('recommendations', '')
            story.append(Paragraph("Рекомендации", subheading_style))
            story.append(Paragraph(compatibility_recommendations, normal_style))
        
        # Новая страница
        story.append(PageBreak())
        
        # Прогноз и рекомендации
        story.append(Paragraph("Прогноз и рекомендации", heading_style))
        
        # Прогноз
        forecast = interpretation_data.get('forecast', '')
        story.append(Paragraph(forecast, normal_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Рекомендации
        recommendations = interpretation_data.get('recommendations', '')
        story.append(Paragraph("Личные рекомендации", subheading_style))
        story.append(Paragraph(recommendations, normal_style))
        
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
        return pdf_path
        
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        return None