"""
Модуль для генерации PDF-отчетов на основе HTML-шаблона и данных интерпретации.
"""

import os
import logging
from datetime import datetime
import jinja2
import weasyprint
from typing import Dict, Any, Optional

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Путь к HTML-шаблону и директории для сохранения PDF
TEMPLATE_FILE = 'pdf_template.html'
PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')

# Создаем директорию для хранения PDF, если она не существует
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)


def get_jinja_template():
    """
    Получает объект шаблона Jinja2 для генерации HTML.
    
    Returns:
        jinja2.Template: Объект шаблона Jinja2
    """
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    return template_env.get_template(TEMPLATE_FILE)


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
        # Получаем шаблон
        template = get_jinja_template()
        
        # Подготавливаем данные для шаблона
        template_data = {
            'user_name': user_data.get('fio', 'Пользователь'),
            'birthdate': user_data.get('birthdate', '').strftime('%d.%m.%Y') if user_data.get('birthdate') else '',
            'current_date': datetime.now().strftime('%d.%m.%Y'),
            'current_year': datetime.now().year,
            
            # Числа из нумерологических расчетов
            'life_path_number': numerology_data.get('life_path_number', ''),
            'expression_number': numerology_data.get('expression_number', ''),
            'soul_number': numerology_data.get('soul_number', ''),
            'personality_number': numerology_data.get('personality_number', ''),
            
            # Данные интерпретации от ИИ
            'introduction': interpretation_data.get('introduction', ''),
            'life_path_interpretation': interpretation_data.get('life_path_interpretation', ''),
            'expression_interpretation': interpretation_data.get('expression_interpretation', ''),
            'soul_interpretation': interpretation_data.get('soul_interpretation', ''),
            'personality_interpretation': interpretation_data.get('personality_interpretation', ''),
            'life_path_detailed': interpretation_data.get('life_path_detailed', ''),
            'expression_detailed': interpretation_data.get('expression_detailed', ''),
            'soul_detailed': interpretation_data.get('soul_detailed', ''),
            'personality_detailed': interpretation_data.get('personality_detailed', ''),
            'forecast': interpretation_data.get('forecast', ''),
            'recommendations': interpretation_data.get('recommendations', '')
        }
        
        # Если это отчет о совместимости, добавляем соответствующие данные
        if report_type == 'compatibility':
            compatibility_data = interpretation_data.get('compatibility', {})
            template_data.update({
                'compatibility_report': True,
                'compatibility_intro': compatibility_data.get('intro', ''),
                'compatibility_score': compatibility_data.get('score', 0),
                'compatibility_strengths': compatibility_data.get('strengths', ''),
                'compatibility_challenges': compatibility_data.get('challenges', ''),
                'compatibility_recommendations': compatibility_data.get('recommendations', '')
            })
        else:
            template_data['compatibility_report'] = False
        
        # Генерируем HTML на основе шаблона
        html_content = template.render(**template_data)
        
        # Формируем имя файла для PDF
        user_id = user_data.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"{user_id}_{report_type}_{timestamp}.pdf"
        pdf_path = os.path.join(PDF_STORAGE_PATH, pdf_filename)
        
        # Генерируем PDF
        weasyprint.HTML(string=html_content).write_pdf(pdf_path)
        
        logger.info(f"PDF отчет успешно сгенерирован: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        return None