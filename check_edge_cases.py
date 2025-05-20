#!/usr/bin/env python
# check_edge_cases.py - Проверка крайних случаев в расчетах

import asyncio
from pprint import pprint
import json
from numerology_core_updated import (
    calculate_numerology_advanced, calculate_compatibility, calculate_numerology,
    reduce_to_arcane, letter_to_number, calculate_digit_sum
)

def test_reduce_to_arcane():
    """Проверка функции приведения к аркану"""
    test_cases = [
        (1, 1),      # Число уже является арканом
        (22, 22),    # Верхняя граница
        (23, 1),     # 23 -> 23-22 = 1
        (44, 22),    # 44 -> 44-22 = 22
        (45, 1),     # 45 -> 45-22 = 23 -> 23-22 = 1
        (0, 22),     # 0 должен преобразоваться в 22
        (10, 10),    # Середина диапазона
        (15, 15),    # Середина диапазона
        (100, 12),   # 100 -> 100-(22*4) = 12
        (999, 9)     # 999 -> 999-(22*45) = 9
    ]
    
    print("=== Тестирование функции reduce_to_arcane ===")
    for input_value, expected_output in test_cases:
        actual_output = reduce_to_arcane(input_value)
        result = "✓" if actual_output == expected_output else "✗"
        print(f"{input_value} -> {actual_output} (ожидалось {expected_output}) {result}")

def test_letter_to_number():
    """Проверка функции преобразования букв в числа"""
    test_cases = [
        ('а', 1), ('б', 2), ('в', 3), ('г', 4), ('д', 5),
        ('е', 6), ('ё', 6), ('ж', 8), ('з', 9), ('и', 1),
        ('й', 2), ('к', 3), ('л', 4), ('м', 5), ('н', 6),
        ('о', 7), ('п', 8), ('р', 9), ('с', 1), ('т', 2),
        ('у', 3), ('ф', 4), ('х', 5), ('ц', 6), ('ч', 7),
        ('ш', 8), ('щ', 9), ('ъ', 1), ('ы', 2), ('ь', 3),
        ('э', 4), ('ю', 5), ('я', 6),
        # Проверка верхнего регистра
        ('А', 1), ('К', 3), ('Я', 6),
        # Проверка невалидных символов
        (' ', 0), ('!', 0), ('1', 0), ('a', 0), ('z', 0)
    ]
    
    print("\n=== Тестирование функции letter_to_number ===")
    failed_tests = []
    for letter, expected_output in test_cases:
        actual_output = letter_to_number(letter)
        result = "✓" if actual_output == expected_output else "✗"
        if actual_output != expected_output:
            failed_tests.append((letter, actual_output, expected_output))
        print(f"'{letter}' -> {actual_output} (ожидалось {expected_output}) {result}")
    
    if failed_tests:
        print("\nОшибки в преобразовании букв:")
        for letter, actual, expected in failed_tests:
            print(f"'{letter}': получено {actual}, ожидалось {expected}")

def test_edge_birthdate_cases():
    """Проверка крайних случаев дат рождения"""
    test_cases = [
        ("01.01.1900", "Иванов Иван"),  # Начало 20 века
        ("31.12.1999", "Петров Петр"),  # Конец 20 века
        ("29.02.2000", "Сидоров Сидор"),  # Високосный год
        ("31.12.2025", "Тестов Тест"),  # Будущая дата
        # Неправильные форматы
        ("2000-01-01", "Формат ИСО"),  # ISO формат
        ("01/01/2000", "Слеш формат"),  # Формат с косой чертой
        # Невалидные даты
        ("30.02.2000", "Несуществующая дата"),  # 30 февраля не существует
        ("31.11.2000", "Несуществующая дата"),  # 31 ноября не существует
        ("00.00.0000", "Нулевая дата")  # Полностью нулевая дата
    ]
    
    print("\n=== Тестирование крайних случаев дат рождения ===")
    for birthdate, fio in test_cases:
        try:
            result = calculate_numerology_advanced(birthdate, fio)
            # Проверяем, есть ли ошибка в результате
            if "error" in result:
                print(f"{birthdate} -> Ошибка: {result['error']}")
            else:
                # Выводим основной аркан (например, МЧ)
                master_number = result["arcanes"]["master_number"]["arcane"]
                print(f"{birthdate} -> Успешный расчёт, МЧ = {master_number}")
        except Exception as e:
            print(f"{birthdate} -> Неперехваченное исключение: {e}")

def test_edge_name_cases():
    """Проверка крайних случаев имен"""
    test_cases = [
        ("01.01.2000", ""),  # Пустое имя
        ("01.01.2000", "И"),  # Очень короткое имя
        ("01.01.2000", "Иван"),  # Только имя без фамилии
        ("01.01.2000", "Иванов Иван Иванович"),  # Полное ФИО
        ("01.01.2000", "ааааааааааааааааааа"),  # Повторяющиеся буквы
        ("01.01.2000", "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"),  # Все буквы алфавита
        ("01.01.2000", "ИвановИван"),  # Без пробела
        ("01.01.2000", "Иванов-Петров Иван"),  # Двойная фамилия
        ("01.01.2000", "Smith John"),  # Латиница
        ("01.01.2000", "Иванов123"),  # С цифрами
        ("01.01.2000", "!@#$%"),  # Только спецсимволы
        ("01.01.2000", "Иванов Иван!"),  # Со спецсимволами
    ]
    
    print("\n=== Тестирование крайних случаев имен ===")
    for birthdate, fio in test_cases:
        try:
            result = calculate_numerology_advanced(birthdate, fio)
            # Проверяем, есть ли ошибка в результате
            if "error" in result:
                print(f"'{fio}' -> Ошибка: {result['error']}")
            else:
                # Выводим уникальные буквы и МЧ
                unique_letters = result["raw_data"]["unique_letters"]
                master_number = result["arcanes"]["master_number"]["arcane"]
                print(f"'{fio}' -> Успешный расчёт, уникальные буквы: '{unique_letters}', МЧ = {master_number}")
        except Exception as e:
            print(f"'{fio}' -> Неперехваченное исключение: {e}")

def test_compatibility_edge_cases():
    """Проверка крайних случаев совместимости"""
    test_cases = [
        # Одинаковые люди
        ("01.01.2000", "Иванов Иван", "01.01.2000", "Иванов Иван"),
        # Люди с одинаковыми параметрами по жизненному пути
        ("01.01.2000", "Иванов Иван", "10.10.2000", "Петров Петр"),
        # Люди с сильно разными параметрами
        ("01.01.1950", "Иванов Иван", "01.01.2020", "Петров Петр"),
        # Невалидные даты для одного из людей
        ("99.99.9999", "Иванов Иван", "01.01.2000", "Петров Петр"),
        # Невалидные даты для обоих людей
        ("99.99.9999", "Иванов Иван", "88.88.8888", "Петров Петр"),
    ]
    
    print("\n=== Тестирование крайних случаев совместимости ===")
    for birthdate1, fio1, birthdate2, fio2 in test_cases:
        try:
            result = calculate_compatibility(birthdate1, fio1, birthdate2, fio2)
            # Проверяем, есть ли ошибка в результате
            if "error" in result:
                print(f"{fio1} ({birthdate1}) и {fio2} ({birthdate2}) -> Ошибка: {result['error']}")
            else:
                # Выводим процент совместимости
                compatibility_percent = result["compatibility"]["percent"]
                karmic_connection = result["karmic_connection"]
                print(f"{fio1} ({birthdate1}) и {fio2} ({birthdate2}) -> Совместимость: {compatibility_percent}%, Кармическая связь: {karmic_connection}")
        except Exception as e:
            print(f"{fio1} и {fio2} -> Неперехваченное исключение: {e}")

def main():
    """Главная функция для запуска всех тестов"""
    print("Запуск проверки крайних случаев...")
    
    test_reduce_to_arcane()
    test_letter_to_number()
    test_edge_birthdate_cases()
    test_edge_name_cases()
    test_compatibility_edge_cases()
    
    print("\nТестирование завершено!")

if __name__ == "__main__":
    main()