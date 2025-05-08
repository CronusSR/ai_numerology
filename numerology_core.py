# numerology_core.py - модуль для нумерологических расчетов
from datetime import datetime
from typing import Dict, Any, List, Tuple

def calculate_digit_sum(number: int) -> int:
    """
    Рассчитывает сумму цифр числа до получения однозначного числа.
    Пример: 28 -> 2 + 8 = 10 -> 1 + 0 = 1
    """
    while number > 9:
        number = sum(int(digit) for digit in str(number))
    return number

def get_life_path_number(birthdate: str) -> int:
    """
    Рассчитывает число жизненного пути на основе даты рождения.
    Формат даты: YYYY-MM-DD
    """
    try:
        date_obj = datetime.strptime(birthdate, "%Y-%m-%d")
        day = date_obj.day
        month = date_obj.month
        year = date_obj.year
        
        day_sum = calculate_digit_sum(day)
        month_sum = calculate_digit_sum(month)
        year_sum = calculate_digit_sum(year)
        
        life_path = day_sum + month_sum + year_sum
        return calculate_digit_sum(life_path)
    except ValueError:
        return 0

def get_expression_number(fio: str) -> int:
    """
    Рассчитывает число выражения на основе ФИО.
    Используется система Пифагора для преобразования букв в числа.
    """
    # Таблица соответствия букв русского алфавита и чисел по системе Пифагора
    ru_letters = {
        'а': 1, 'б': 2, 'в': 3, 'г': 4, 'д': 5, 'е': 6, 'ё': 7, 'ж': 8, 'з': 9,
        'и': 1, 'й': 2, 'к': 3, 'л': 4, 'м': 5, 'н': 6, 'о': 7, 'п': 8, 'р': 9,
        'с': 1, 'т': 2, 'у': 3, 'ф': 4, 'х': 5, 'ц': 6, 'ч': 7, 'ш': 8, 'щ': 9,
        'ъ': 1, 'ы': 2, 'ь': 3, 'э': 4, 'ю': 5, 'я': 6
    }
    
    # Таблица соответствия букв английского алфавита и чисел по системе Пифагора
    en_letters = {
        'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9,
        'j': 1, 'k': 2, 'l': 3, 'm': 4, 'n': 5, 'o': 6, 'p': 7, 'q': 8, 'r': 9,
        's': 1, 't': 2, 'u': 3, 'v': 4, 'w': 5, 'x': 6, 'y': 7, 'z': 8
    }
    
    fio = fio.lower()
    total = 0
    
    for char in fio:
        if char in ru_letters:
            total += ru_letters[char]
        elif char in en_letters:
            total += en_letters[char]
    
    return calculate_digit_sum(total)

def get_soul_urge_number(fio: str) -> int:
    """
    Рассчитывает число души на основе гласных букв в ФИО.
    """
    ru_vowels = {'а': 1, 'е': 6, 'ё': 7, 'и': 1, 'о': 7, 'у': 3, 'ы': 2, 'э': 4, 'ю': 5, 'я': 6}
    en_vowels = {'a': 1, 'e': 5, 'i': 9, 'o': 6, 'u': 3, 'y': 7}
    
    fio = fio.lower()
    total = 0
    
    for char in fio:
        if char in ru_vowels:
            total += ru_vowels[char]
        elif char in en_vowels:
            total += en_vowels[char]
    
    return calculate_digit_sum(total)

def get_personality_number(fio: str) -> int:
    """
    Рассчитывает число личности на основе согласных букв в ФИО.
    """
    ru_consonants = {
        'б': 2, 'в': 3, 'г': 4, 'д': 5, 'ж': 8, 'з': 9,
        'й': 2, 'к': 3, 'л': 4, 'м': 5, 'н': 6, 'п': 8, 'р': 9,
        'с': 1, 'т': 2, 'ф': 4, 'х': 5, 'ц': 6, 'ч': 7, 'ш': 8, 'щ': 9,
        'ъ': 1, 'ь': 3
    }
    en_consonants = {
        'b': 2, 'c': 3, 'd': 4, 'f': 6, 'g': 7, 'h': 8,
        'j': 1, 'k': 2, 'l': 3, 'm': 4, 'n': 5, 'p': 7, 'q': 8, 'r': 9,
        's': 1, 't': 2, 'v': 4, 'w': 5, 'x': 6, 'z': 8
    }
    
    fio = fio.lower()
    total = 0
    
    for char in fio:
        if char in ru_consonants:
            total += ru_consonants[char]
        elif char in en_consonants:
            total += en_consonants[char]
    
    return calculate_digit_sum(total)

def get_destiny_number(fio: str) -> int:
    """
    Рассчитывает число судьбы на основе ФИО.
    """
    return get_expression_number(fio)

def get_karmic_lessons(fio: str) -> List[int]:
    """
    Определяет кармические уроки на основе отсутствующих чисел в ФИО.
    """
    ru_letters = {
        'а': 1, 'б': 2, 'в': 3, 'г': 4, 'д': 5, 'е': 6, 'ё': 7, 'ж': 8, 'з': 9,
        'и': 1, 'й': 2, 'к': 3, 'л': 4, 'м': 5, 'н': 6, 'о': 7, 'п': 8, 'р': 9,
        'с': 1, 'т': 2, 'у': 3, 'ф': 4, 'х': 5, 'ц': 6, 'ч': 7, 'ш': 8, 'щ': 9,
        'ъ': 1, 'ы': 2, 'ь': 3, 'э': 4, 'ю': 5, 'я': 6
    }
    
    en_letters = {
        'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9,
        'j': 1, 'k': 2, 'l': 3, 'm': 4, 'n': 5, 'o': 6, 'p': 7, 'q': 8, 'r': 9,
        's': 1, 't': 2, 'u': 3, 'v': 4, 'w': 5, 'x': 6, 'y': 7, 'z': 8
    }
    
    # Счетчик для всех возможных чисел от 1 до 9
    number_counts = {i: 0 for i in range(1, 10)}
    
    fio = fio.lower()
    
    for char in fio:
        if char in ru_letters:
            number = ru_letters[char]
            number_counts[number] += 1
        elif char in en_letters:
            number = en_letters[char]
            number_counts[number] += 1
    
    # Кармические уроки - это числа, которые отсутствуют в имени
    karmic_lessons = [num for num, count in number_counts.items() if count == 0]
    
    return karmic_lessons

def get_personal_year(birthdate: str) -> int:
    """
    Рассчитывает число личного года на основе даты рождения и текущего года.
    """
    try:
        date_obj = datetime.strptime(birthdate, "%Y-%m-%d")
        day = date_obj.day
        month = date_obj.month
        current_year = datetime.now().year
        
        personal_year = day + month + current_year
        return calculate_digit_sum(personal_year)
    except ValueError:
        return 0

def calculate_numerology(birthdate: str, fio: str) -> Dict[str, Any]:
    """
    Выполняет полный набор нумерологических расчетов.
    """
    life_path = get_life_path_number(birthdate)
    expression = get_expression_number(fio)
    soul_urge = get_soul_urge_number(fio)
    personality = get_personality_number(fio)
    destiny = get_destiny_number(fio)
    karmic_lessons = get_karmic_lessons(fio)
    personal_year = get_personal_year(birthdate)
    
    # Формирование матрицы Пифагора
    date_obj = datetime.strptime(birthdate, "%Y-%m-%d")
    day_str = str(date_obj.day)
    month_str = str(date_obj.month)
    year_str = str(date_obj.year)
    date_digits = day_str + month_str + year_str
    
    # Подсчет частоты каждой цифры
    pythagoras_matrix = {str(i): date_digits.count(str(i)) for i in range(1, 10)}
    
    return {
        "life_path": life_path,
        "expression": expression,
        "soul_urge": soul_urge,
        "personality": personality,
        "destiny": destiny,
        "karmic_lessons": karmic_lessons,
        "personal_year": personal_year,
        "pythagoras_matrix": pythagoras_matrix,
        "birth_data": {
            "date": birthdate,
            "day": date_obj.day,
            "month": date_obj.month,
            "year": date_obj.year
        },
        "fio": fio
    }

def calculate_compatibility(
    birthdate1: str, fio1: str,
    birthdate2: str, fio2: str
) -> Dict[str, Any]:
    """
    Рассчитывает совместимость между двумя людьми на основе их нумерологических данных.
    """
    person1 = calculate_numerology(birthdate1, fio1)
    person2 = calculate_numerology(birthdate2, fio2)
    
    # Расчет базовой совместимости (от 1 до 10)
    # На основе сравнения жизненных путей
    life_path_compatibility = 10 - abs(person1["life_path"] - person2["life_path"])
    
    # Расчет эмоциональной совместимости
    emotional_compatibility = 10 - abs(person1["soul_urge"] - person2["soul_urge"])
    
    # Расчет интеллектуальной совместимости
    intellectual_compatibility = 10 - abs(person1["expression"] - person2["expression"])
    
    # Расчет физической совместимости
    physical_compatibility = 10 - abs(person1["personality"] - person2["personality"])
    
    # Общая совместимость (средневзвешенное)
    total_compatibility = (
        life_path_compatibility * 0.4 + 
        emotional_compatibility * 0.3 + 
        intellectual_compatibility * 0.2 + 
        physical_compatibility * 0.1
    )
    
    # Расчет кармической связи
    karmic_connection = False
    if person1["life_path"] == person2["life_path"]:
        karmic_connection = True
    
    # Расчет потенциальных сложностей
    challenges = []
    if abs(person1["life_path"] - person2["life_path"]) > 5:
        challenges.append("Разные жизненные пути")
    if abs(person1["soul_urge"] - person2["soul_urge"]) > 5:
        challenges.append("Разные эмоциональные потребности")
    
    return {
        "person1": person1,
        "person2": person2,
        "compatibility": {
            "life_path": life_path_compatibility,
            "emotional": emotional_compatibility,
            "intellectual": intellectual_compatibility,
            "physical": physical_compatibility,
            "total": round(total_compatibility, 1)
        },
        "karmic_connection": karmic_connection,
        "challenges": challenges
    }