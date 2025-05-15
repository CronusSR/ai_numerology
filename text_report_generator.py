"""
Простой генератор текстовых отчетов вместо PDF.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к директории для сохранения отчетов
PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')

# Создаем директорию для хранения отчетов, если она не существует
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

def generate_pdf(user_data: Dict[str, Any], numerology_data: Dict[str, Any],
                interpretation_data: Dict[str, Any], report_type: str = 'full') -> Optional[str]:
    """
    Генерирует текстовый отчет (вместо PDF) и возвращает путь к файлу.
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
        
        # Формируем имя файла
        user_id = user_data.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{user_id}_{report_type}_{timestamp}.txt"
        filepath = os.path.join(PDF_STORAGE_PATH, filename)
        
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
            f.write(f"{interpretation_data.get('introduction', 'Нумерологический анализ на основе ваших персональных данных.')}\n\n")
            
            # Ключевые числа
            f.write("КЛЮЧЕВЫЕ ЧИСЛА ВАШЕЙ СУДЬБЫ\n")
            f.write(f"{'-' * 40}\n")
            
            # Число жизненного пути
            lp = numerology_data.get('life_path', '')
            f.write(f"Число жизненного пути: {lp}\n")
            f.write(f"{interpretation_data.get('life_path_interpretation', '')}\n\n")
            
            # Число выражения
            exp = numerology_data.get('expression', '')
            f.write(f"Число выражения: {exp}\n")
            f.write(f"{interpretation_data.get('expression_interpretation', '')}\n\n")
            
            # Число души
            soul = numerology_data.get('soul_urge', '')
            f.write(f"Число души: {soul}\n")
            f.write(f"{interpretation_data.get('soul_interpretation', '')}\n\n")
            
            # Число личности
            pers = numerology_data.get('personality', '')
            f.write(f"Число личности: {pers}\n")
            f.write(f"{interpretation_data.get('personality_interpretation', '')}\n\n")
            
            # Подробный анализ
            f.write("ПОДРОБНЫЙ АНАЛИЗ ЧИСЕЛ\n")
            f.write(f"{'-' * 40}\n")
            
            f.write(f"Число жизненного пути: {lp}\n")
            f.write(f"{interpretation_data.get('life_path_detailed', '')}\n\n")
            
            f.write(f"Число выражения: {exp}\n")
            f.write(f"{interpretation_data.get('expression_detailed', '')}\n\n")
            
            f.write(f"Число души: {soul}\n")
            f.write(f"{interpretation_data.get('soul_detailed', '')}\n\n")
            
            f.write(f"Число личности: {pers}\n")
            f.write(f"{interpretation_data.get('personality_detailed', '')}\n\n")
            
            # Дополнительная информация для отчета о совместимости
            if report_type == 'compatibility':
                f.write("АНАЛИЗ СОВМЕСТИМОСТИ\n")
                f.write(f"{'-' * 40}\n")
                
                score = interpretation_data.get('score', 0)
                f.write(f"Общая совместимость: {score}%\n\n")
                
                f.write("Сильные стороны отношений:\n")
                f.write(f"{interpretation_data.get('strengths', '')}\n\n")
                
                f.write("Возможные трудности:\n")
                f.write(f"{interpretation_data.get('challenges', '')}\n\n")
                
                f.write("Рекомендации:\n")
                f.write(f"{interpretation_data.get('recommendations', '')}\n\n")
            
            # Прогноз и рекомендации
            f.write("ПРОГНОЗ И РЕКОМЕНДАЦИИ\n")
            f.write(f"{'-' * 40}\n")
            
            f.write(f"{interpretation_data.get('forecast', '')}\n\n")
            
            f.write("Личные рекомендации:\n")
            f.write(f"{interpretation_data.get('recommendations', '')}\n\n")
            
            # Футер
            f.write(f"{'=' * 50}\n")
            f.write(f"© ИИ-Нумеролог {datetime.now().year}. Все права защищены.\n")
            f.write("Данный отчет сгенерирован с использованием искусственного интеллекта.\n")
            f.write("Для получения обновлений и еженедельных прогнозов подпишитесь в Telegram-боте.\n")
        
        logger.info(f"Текстовый отчет успешно сгенерирован: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}")
        return None