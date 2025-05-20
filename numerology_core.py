# numerology_core.py - модуль для нумерологических расчетов
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

CALCULATIONS_DIR = os.environ.get('CALCULATIONS_DIR', './calculations')

# Функция для сохранения результатов расчетов в файл
def save_calculation_to_file(birthdate: str, fio: str, calculation_data: Dict[str, Any]) -> str:
    """
    Сохраняет результаты расчетов в файл для отладки и мониторинга.
    
    Args:
        birthdate: Дата рождения
        fio: ФИО
        calculation_data: Данные расчета
        
    Returns:
        str: Путь к созданному файлу
    """
    try:
        # Создаем директорию, если она не существует
        os.makedirs(CALCULATIONS_DIR, exist_ok=True)
        
        # Формируем имя файла на основе даты, времени и ФИО
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sanitized_fio = ''.join(c if c.isalnum() else '_' for c in fio)
        filename = f"{timestamp}_{sanitized_fio}.md"
        filepath = os.path.join(CALCULATIONS_DIR, filename)
        
        # Получаем Markdown-отчет
        markdown_report = calculation_data.get("report", {}).get("markdown", "")
        
        # Сохраняем в файл
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Нумерологический расчет\n\n")
            f.write(f"Дата рождения: {birthdate}\n")
            f.write(f"ФИО: {fio}\n")
            f.write(f"Дата и время расчета: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
            f.write(f"## Параметры расчета\n\n")
            f.write(markdown_report)
            f.write("\n\n## Примечание\n\n")
            f.write("Этот файл содержит данные, которые отправляются на n8n для интерпретации.\n")
            f.write("Сам анализ и формирование отчета происходит на стороне n8n с использованием ИИ.\n")
        
        return filepath
    except Exception as e:
        # В случае ошибки просто логируем её и продолжаем работу
        print(f"Ошибка при сохранении расчета в файл: {e}")
        return ""

def calculate_digit_sum(number: int) -> int:
    """
    Рассчитывает сумму цифр числа до получения однозначного числа.
    Пример: 28 -> 2 + 8 = 10 -> 1 + 0 = 1
    """
    while number > 9:
        number = sum(int(digit) for digit in str(number))
    return number

def reduce_to_arcane(number: int) -> int:
    """
    Приводит число к значению аркана (от 1 до 22).
    Если число больше 22, вычитаем 22, пока не станет <= 22.
    Если результат равен 0, считаем как 22.
    """
    while number > 22:
        number -= 22
    
    if number == 0:
        number = 22
        
    return number

def get_arcane_percent(arcane: int) -> float:
    """
    Возвращает процентное значение аркана согласно таблице.
    """
    arcane_percentages = {
        1: 27.0, 2: 22.5, 3: 36.0, 4: 99.0, 5: 31.5,
        6: 18.0, 7: 54.0, 8: 58.5, 9: 40.5, 10: 81.0,
        11: 67.5, 12: 9.0, 13: 90.0, 14: 45.0, 15: 72.0,
        16: 94.5, 17: 63.0, 18: 13.5, 19: 85.5, 20: 4.5,
        21: 49.5, 22: 76.5
    }
    
    return arcane_percentages.get(arcane, 0.0)

def get_arcane_type(arcane: int, type_key: str) -> str:
    """
    Возвращает тип аркана: Инь/Ян или Судьба/Воля в зависимости от ключа.
    """
    if type_key == "yin_yang":
        yin_arcanes = [2, 3, 6, 12, 14, 15, 17, 18, 20, 21, 22]
        if arcane in yin_arcanes:
            return "ИНЬ"
        else:
            return "ЯН"
    
    elif type_key == "fate_will":
        fate_arcanes = [1, 2, 5, 6, 9, 10, 13, 14, 15, 16, 20]
        if arcane in fate_arcanes:
            return "СУДЬБА"
        else:
            return "ВОЛЯ"
    
    return "НЕИЗВЕСТНО"

def letter_to_number(letter: str) -> int:
    """
    Преобразует букву русского алфавита в числовое значение согласно таблице.
    """
    russian_letters = {
        'а': 1, 'б': 2, 'в': 3, 'г': 4, 'д': 5, 'е': 6, 'ё': 6, 'ж': 8, 'з': 9,
        'и': 1, 'й': 2, 'к': 3, 'л': 4, 'м': 5, 'н': 6, 'о': 7, 'п': 8, 'р': 9,
        'с': 1, 'т': 2, 'у': 3, 'ф': 4, 'х': 5, 'ц': 6, 'ч': 7, 'ш': 8, 'щ': 9,
        'ъ': 1, 'ы': 2, 'ь': 3, 'э': 4, 'ю': 5, 'я': 6
    }
    
    letter = letter.lower()
    return russian_letters.get(letter, 0)

def get_personal_year(birthdate: str) -> int:
    """
    Рассчитывает число личного года на основе даты рождения и текущего года.
    """
    try:
        # Преобразуем строку в объект datetime
        if '-' in birthdate:
            date_obj = datetime.strptime(birthdate, "%Y-%m-%d")
        else:
            date_obj = datetime.strptime(birthdate, "%d.%m.%Y")
            
        day = date_obj.day
        month = date_obj.month
        current_year = datetime.now().year
        
        personal_year = day + month + current_year
        return reduce_to_arcane(personal_year)
    except ValueError:
        return 0

def calculate_master_number(fio: str) -> Tuple[int, str]:
    """
    Рассчитывает МЧ (Мастер Число) на основе ФИО.
    Возвращает кортеж (МЧ, строка с уникальными буквами)
    """
    # Берем только фамилию и имя
    parts = fio.split()
    if len(parts) >= 2:
        name_surname = parts[0] + parts[1]  # фамилия + имя
    else:
        name_surname = fio  # если передана только одна часть
    
    # Удаляем дубликаты букв, сохраняя порядок
    unique_letters = ""
    seen_letters = set()
    
    for char in name_surname.lower():
        if char.isalpha() and char not in seen_letters:
            seen_letters.add(char)
            unique_letters += char
    
    # Преобразуем буквы в числа и суммируем
    total = sum(letter_to_number(letter) for letter in unique_letters)
    
    # Приводим к значению аркана
    master_number = reduce_to_arcane(total)
    
    return master_number, unique_letters

def calculate_numerology_advanced(birthdate: str, fio: str) -> Dict[str, Any]:
    """
    Выполняет расширенный набор нумерологических расчетов согласно новой логике.
    
    Args:
        birthdate: Дата рождения в формате YYYY-MM-DD или DD.MM.YYYY
        fio: ФИО (фамилия, имя, отчество)
        
    Returns:
        Dict: Словарь с результатами расчетов
    """
    # Парсим дату рождения
    try:
        if '-' in birthdate:
            date_obj = datetime.strptime(birthdate, "%Y-%m-%d")
        else:
            date_obj = datetime.strptime(birthdate, "%d.%m.%Y")
        
        day = date_obj.day
        month = date_obj.month
        year = date_obj.year
    except ValueError:
        # Возвращаем ошибку при неверном формате даты
        return {"error": "Неверный формат даты рождения"}
    
    # Вычисляем Дтч (день) и приводим к аркану
    dt_arcane = reduce_to_arcane(day)
    
    # Вычисляем Мтч (месяц)
    mt_arcane = month  # месяц уже в пределах от 1 до 12
    
    # Вычисляем Гтч (год)
    year_sum = sum(int(digit) for digit in str(year))
    gt_arcane = reduce_to_arcane(year_sum)
    
    # Вычисляем МЧ (Мастер Число)
    master_number, unique_letters = calculate_master_number(fio)
    
    # Вычисляем ТМЧ (Тип Мастер Числа): ИНЬ или ЯН
    tm_type = get_arcane_type(master_number, "yin_yang")
    
    # Вычисляем ПДМ (Природа Души Матрицы): СУДЬБА или ВОЛЯ
    pdm_type = get_arcane_type(master_number, "fate_will")
    
    # Вычисляем ЗК (Земной Круг)
    zk_arcane = reduce_to_arcane(dt_arcane + (2 * mt_arcane) + gt_arcane)
    
    # Вычисляем ПЧХ (Потенциал Человеческий)
    pch_arcane = reduce_to_arcane((4 * dt_arcane) + (3 * mt_arcane) + (3 * gt_arcane))
    
    # Вычисляем КЧХ (Кармический Человеческий)
    kch_value = dt_arcane - gt_arcane
    if kch_value <= 0:
        kch_value += 22
    kch_arcane = reduce_to_arcane(kch_value)
    
    # Вычисляем ПР (Планетарный Резонанс)
    pr_arcane = reduce_to_arcane((6 * dt_arcane) + (6 * mt_arcane) + (5 * gt_arcane))
    
    # Вычисляем СЗ (Социальное Значение)
    sz_arcane = reduce_to_arcane(dt_arcane + mt_arcane + gt_arcane)
    
    # Вычисляем ОПВ (Отношение к Первичной Власти)
    opv_value = dt_arcane - mt_arcane
    if opv_value <= 0:
        opv_value += 22
    opv_arcane = reduce_to_arcane(opv_value)
    
    # Вычисляем ЭБ (Энергетический Баланс)
    eb_value = mt_arcane - gt_arcane
    if eb_value <= 0:
        eb_value += 22
    eb_arcane = reduce_to_arcane(eb_value)
    
    # Вычисляем БС (Блок Судьбы)
    bs_arcane = reduce_to_arcane(master_number + dt_arcane + mt_arcane)
    
    # Вычисляем СТ (Статус)
    x_percent = (get_arcane_percent(master_number) + get_arcane_percent(pch_arcane)) / 2
    y_percent = (get_arcane_percent(bs_arcane) + get_arcane_percent(kch_arcane)) / 2
    st_percent = x_percent - y_percent
    
    # Определяем аркан СТ
    st_arcane = 0
    min_diff = float('inf')
    for arcane in range(1, 23):
        diff = abs(get_arcane_percent(arcane) - abs(st_percent))
        if diff < min_diff:
            min_diff = diff
            st_arcane = arcane
    
    # Формируем результат в требуемом формате
    formatted_date = date_obj.strftime("%d.%m.%Y")
    
    result = {
        "raw_data": {
            "birthdate": formatted_date,
            "fio": fio,
            "unique_letters": unique_letters
        },
        "arcanes": {
            "dt": {
                "arcane": dt_arcane,
                "percent": get_arcane_percent(dt_arcane)
            },
            "mt": {
                "arcane": mt_arcane,
                "percent": get_arcane_percent(mt_arcane),
                "type": tm_type
            },
            "gt": {
                "arcane": gt_arcane,
                "percent": get_arcane_percent(gt_arcane)
            },
            "master_number": {
                "arcane": master_number,
                "percent": get_arcane_percent(master_number),
                "tm_type": tm_type,
                "pdm_type": pdm_type
            },
            "zk": {
                "arcane": zk_arcane,
                "percent": get_arcane_percent(zk_arcane)
            },
            "pch": {
                "arcane": pch_arcane,
                "percent": get_arcane_percent(pch_arcane)
            },
            "kch": {
                "arcane": kch_arcane,
                "percent": get_arcane_percent(kch_arcane)
            },
            "pr": {
                "arcane": pr_arcane,
                "percent": get_arcane_percent(pr_arcane)
            },
            "sz": {
                "arcane": sz_arcane,
                "percent": get_arcane_percent(sz_arcane)
            },
            "opv": {
                "arcane": opv_arcane,
                "percent": get_arcane_percent(opv_arcane)
            },
            "eb": {
                "arcane": eb_arcane,
                "percent": get_arcane_percent(eb_arcane)
            },
            "bs": {
                "arcane": bs_arcane,
                "percent": get_arcane_percent(bs_arcane)
            },
            "st": {
                "arcane": st_arcane,
                "percent": st_percent
            }
        }
    }
    
    # Формируем текстовый отчет в формате Markdown
    markdown_report = f"""# Параметры по корневой дате {formatted_date}
## Параметры "Дт"
### Аркан_Дт={dt_arcane}
### Процент_Дт={get_arcane_percent(dt_arcane):.1f}
## Параметры "Мт"
### Аркан_Мт={mt_arcane}
### Процент_Мт={get_arcane_percent(mt_arcane):.1f}
### Тип_Мт={tm_type}
## Параметры "Гт"
### Аркан_Гт={gt_arcane}
### Процент_Гт={get_arcane_percent(gt_arcane):.1f}
## Параметры "МЧ"
### Аркан_МЧ={master_number}
### Процент_МЧ={get_arcane_percent(master_number):.1f}
### Тип_МЧ={tm_type}
### ПДМ_МЧ={pdm_type}
## Параметры "ЗК"
### Аркан_ЗК={zk_arcane}
### Процент_ЗК={get_arcane_percent(zk_arcane):.1f}
## Параметры "ПЧХ"
### Аркан_ПЧХ={pch_arcane}
### Процент_ПЧХ={get_arcane_percent(pch_arcane):.1f}
## Параметры "КЧХ"
### Аркан_КЧХ={kch_arcane}
### Процент_КЧХ={get_arcane_percent(kch_arcane):.1f}
## Параметры "ПР"
### Аркан_ПР={pr_arcane}
### Процент_ПР={get_arcane_percent(pr_arcane):.1f}
## Параметры "СЗ"
### Аркан_СЗ={sz_arcane}
### Процент_СЗ={get_arcane_percent(sz_arcane):.1f}
## Параметры "ОПВ"
### Аркан_ОПВ={opv_arcane}
### Процент_ОПВ={get_arcane_percent(opv_arcane):.1f}
## Параметры "ЭБ"
### Аркан_ЭБ={eb_arcane}
### Процент_ЭБ={get_arcane_percent(eb_arcane):.1f}
## Параметры "БС"
### Аркан_БС={bs_arcane}
### Процент_БС={get_arcane_percent(bs_arcane):.1f}
## Параметры "СТ"
### Аркан_СТ={st_arcane}
### Процент_СТ={st_percent:.1f}
"""
    
    result["report"] = {
        "markdown": markdown_report,
        "unique_letters": unique_letters
    }
    
    return result

def calculate_numerology(birthdate: str, fio: str) -> Dict[str, Any]:
    """
    Совместимая версия функции для существующего кода.
    Оставляет предыдущие поля и добавляет новые данные.
    """
    advanced_results = calculate_numerology_advanced(birthdate, fio)
    
    # Проверка на ошибку
    if "error" in advanced_results:
        return {"error": advanced_results["error"]}
    
    # Извлекаем данные из расширенных результатов
    arcanes = advanced_results.get("arcanes", {})
    
    # Собираем совместимый результат
    result = {
        # Сохраняем оригинальные поля для обратной совместимости
        "life_path": arcanes.get("sz", {}).get("arcane", 0),
        "expression": arcanes.get("master_number", {}).get("arcane", 0),
        "soul_urge": arcanes.get("zk", {}).get("arcane", 0),
        "personality": arcanes.get("pch", {}).get("arcane", 0),
        "destiny": arcanes.get("bs", {}).get("arcane", 0),
        "karmic_lessons": [],  # Не используется в новой логике
        "personal_year": arcanes.get("pr", {}).get("arcane", 0),
        "pythagoras_matrix": {},  # Не используется в новой логике
        
        # Добавляем данные рождения в оригинальном формате
        "birth_data": {
            "date": birthdate,
            "day": advanced_results.get("raw_data", {}).get("birthdate", "").split(".")[0],
            "month": advanced_results.get("raw_data", {}).get("birthdate", "").split(".")[1],
            "year": advanced_results.get("raw_data", {}).get("birthdate", "").split(".")[2]
        },
        "fio": fio,
        
        # Добавляем новые поля
        "advanced_data": advanced_results,
        "report_text": advanced_results.get("report", {}).get("markdown", "")
    }
    
    # Сохраняем расчеты в файл для отладки и мониторинга
    save_calculation_to_file(birthdate, fio, advanced_results)
    
    return result

def calculate_compatibility(
    birthdate1: str, fio1: str,
    birthdate2: str, fio2: str
) -> Dict[str, Any]:
    """
    Рассчитывает совместимость между двумя людьми на основе их нумерологических данных.
    """
    # Рассчитываем данные для обоих людей
    person1 = calculate_numerology_advanced(birthdate1, fio1)
    person2 = calculate_numerology_advanced(birthdate2, fio2)
    
    # Проверяем наличие ошибок
    if "error" in person1:
        return {"error": f"Ошибка в данных первого человека: {person1.get('error')}"}
    if "error" in person2:
        return {"error": f"Ошибка в данных второго человека: {person2.get('error')}"}
    
    # Получаем основные арканы для расчета совместимости
    p1_arcanes = person1.get("arcanes", {})
    p2_arcanes = person2.get("arcanes", {})
    
    # Расчет базовой совместимости (от 1 до 10)
    # На основе сравнения арканов судьбы и личности
    life_path_diff = abs(p1_arcanes.get("sz", {}).get("arcane", 0) - p2_arcanes.get("sz", {}).get("arcane", 0))
    life_path_compatibility = min(10, 10 - life_path_diff * 0.5)
    
    # Расчет эмоциональной совместимости на основе арканов души
    soul_diff = abs(p1_arcanes.get("zk", {}).get("arcane", 0) - p2_arcanes.get("zk", {}).get("arcane", 0))
    emotional_compatibility = min(10, 10 - soul_diff * 0.5)
    
    # Расчет интеллектуальной совместимости на основе мастер-чисел
    master_diff = abs(p1_arcanes.get("master_number", {}).get("arcane", 0) - p2_arcanes.get("master_number", {}).get("arcane", 0))
    intellectual_compatibility = min(10, 10 - master_diff * 0.5)
    
    # Расчет физической совместимости на основе арканов личности
    pers_diff = abs(p1_arcanes.get("pch", {}).get("arcane", 0) - p2_arcanes.get("pch", {}).get("arcane", 0))
    physical_compatibility = min(10, 10 - pers_diff * 0.5)
    
    # Общая совместимость (средневзвешенное)
    total_compatibility = (
        life_path_compatibility * 0.4 + 
        emotional_compatibility * 0.3 + 
        intellectual_compatibility * 0.2 + 
        physical_compatibility * 0.1
    )
    
    # Расчет кармической связи
    karmic_connection = False
    if (p1_arcanes.get("sz", {}).get("arcane", 0) == p2_arcanes.get("sz", {}).get("arcane", 0)) or \
       (p1_arcanes.get("master_number", {}).get("arcane", 0) == p2_arcanes.get("master_number", {}).get("arcane", 0)):
        karmic_connection = True
    
    # Расчет потенциальных сложностей
    challenges = []
    if abs(p1_arcanes.get("sz", {}).get("arcane", 0) - p2_arcanes.get("sz", {}).get("arcane", 0)) > 5:
        challenges.append("Разные жизненные пути")
    if abs(p1_arcanes.get("zk", {}).get("arcane", 0) - p2_arcanes.get("zk", {}).get("arcane", 0)) > 5:
        challenges.append("Разные эмоциональные потребности")
    if p1_arcanes.get("master_number", {}).get("tm_type", "") != p2_arcanes.get("master_number", {}).get("tm_type", ""):
        challenges.append("Противоположные энергетические типы (Инь/Ян)")
    
    # Формируем отчет о совместимости в формате Markdown
    compatibility_report = f"""# Анализ совместимости
## Общие параметры
### Совместимость_Общая={round(total_compatibility * 10, 1)}%
### Совместимость_Жизненные_Пути={round(life_path_compatibility * 10, 1)}%
### Совместимость_Эмоциональная={round(emotional_compatibility * 10, 1)}%
### Совместимость_Интеллектуальная={round(intellectual_compatibility * 10, 1)}%
### Совместимость_Физическая={round(physical_compatibility * 10, 1)}%
### Кармическая_Связь={"Да" if karmic_connection else "Нет"}

## Аркан Совместимости
### Аркан_С1={p1_arcanes.get("master_number", {}).get("arcane", 0)}
### Аркан_С2={p2_arcanes.get("master_number", {}).get("arcane", 0)}
### Тип_С1={p1_arcanes.get("master_number", {}).get("tm_type", "")}
### Тип_С2={p2_arcanes.get("master_number", {}).get("tm_type", "")}

## Карта Совместимости
### Карта_С1={person1.get("report", {}).get("markdown", "")}
### Карта_С2={person2.get("report", {}).get("markdown", "")}
"""
    
    # Формируем результат для совместимости
    result = {
        "person1": person1,
        "person2": person2,
        "compatibility": {
            "life_path": round(life_path_compatibility, 1),
            "emotional": round(emotional_compatibility, 1),
            "intellectual": round(intellectual_compatibility, 1),
            "physical": round(physical_compatibility, 1),
            "total": round(total_compatibility, 1),
            "percent": round(total_compatibility * 10, 1)  # в процентах
        },
        "karmic_connection": karmic_connection,
        "challenges": challenges,
        "report_text": compatibility_report
    }
    
    # Сохраняем расчеты совместимости в файл для отладки и мониторинга
    save_path = os.path.join(CALCULATIONS_DIR, "compatibility")
    os.makedirs(save_path, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    sanitized_fio1 = ''.join(c if c.isalnum() else '_' for c in fio1)
    sanitized_fio2 = ''.join(c if c.isalnum() else '_' for c in fio2)
    filename = f"{timestamp}_{sanitized_fio1}_and_{sanitized_fio2}.md"
    filepath = os.path.join(save_path, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Расчет совместимости\n\n")
            f.write(f"Первый человек: {fio1}, {birthdate1}\n")
            f.write(f"Второй человек: {fio2}, {birthdate2}\n")
            f.write(f"Дата и время расчета: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
            f.write(compatibility_report)
            f.write("\n\n## Примечание\n\n")
            f.write("Этот файл содержит данные, которые отправляются на n8n для интерпретации.\n")
            f.write("Сам анализ и формирование отчета происходит на стороне n8n с использованием ИИ.\n")
    except Exception as e:
        print(f"Ошибка при сохранении расчета совместимости в файл: {e}")
    
    return result

def parse_text_to_full_report(text: str) -> Dict[str, Any]:
    """
    Разбирает текстовый ответ от n8n в структурированный формат для полного отчета.
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
    Разбирает текстовый ответ от n8n в структурированный формат для отчета о совместимости.
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