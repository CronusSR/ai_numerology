#!/usr/bin/env python
# test_new_numerology.py - Тестирование обновленного модуля расчетов

import asyncio
from pprint import pprint
import json
from numerology_core_updated import calculate_numerology_advanced, calculate_compatibility, calculate_numerology

async def test_single_calculation():
    """Тестирование расчетов для одного человека"""
    # Тестовые данные
    print("\n=== Тестирование на примере из документации ===")
    birthdate_doc = "14.03.1995"
    fio_doc = "КАРЛЮК ОЛЬГА ЕВГЕНЬЕВНА"
    
    result_doc = calculate_numerology_advanced(birthdate_doc, fio_doc)
    
    print("Отчет в формате Markdown (пример из документации):")
    print(result_doc["report"]["markdown"])
    
    # Тестовые данные
    print("\n=== Тестирование на произвольных данных ===")
    birthdate = "09.12.2002"
    fio = "Иванов Иван Иванович"
    
    # Выполнение расчетов
    result = calculate_numerology_advanced(birthdate, fio)
    
    print("\nОтчет в формате Markdown:")
    print(result["report"]["markdown"])
    
    print("\nВсе данные:")
    pprint(result)
    
    # Проверим, что все ключевые аркана рассчитаны правильно
    unique_letters = result["raw_data"]["unique_letters"]
    print(f"\nУникальные буквы: {unique_letters}")
    
    # Сохраняем в файл для проверки
    with open("advanced_calculation_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    print("\n\n=== Совместимый расчет (для передачи в существующий код) ===")
    compat_result = calculate_numerology(birthdate, fio)
    print("Отчет в формате Markdown:")
    print(compat_result["report_text"])
    
    # Сохраняем в файл для проверки
    with open("compatible_calculation_result.json", "w", encoding="utf-8") as f:
        json.dump(compat_result, f, ensure_ascii=False, indent=4)
    
    # Проверим обработку некорректной даты
    print("\n=== Проверка обработки ошибок ===")
    invalid_birthdate = "99.99.9999"
    invalid_result = calculate_numerology(invalid_birthdate, fio)
    print(f"Результат с некорректной датой: {invalid_result}")

async def test_compatibility_calculation():
    """Тестирование расчетов совместимости"""
    # Тестовые данные
    birthdate1 = "09.12.2002"
    fio1 = "Иванов Иван Иванович"
    birthdate2 = "15.05.1995"
    fio2 = "Петрова Мария Сергеевна"
    
    # Выполнение расчетов совместимости
    result = calculate_compatibility(birthdate1, fio1, birthdate2, fio2)
    
    print("\n=== Расчет совместимости ===")
    print("Отчет в формате Markdown:")
    print(result["report_text"])
    
    print("\nВсе данные:")
    pprint(result)
    
    # Сохраняем в файл для проверки
    with open("compatibility_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    # Проверим обработку некорректной даты
    print("\n=== Проверка обработки ошибок в совместимости ===")
    invalid_birthdate = "99.99.9999"
    invalid_result = calculate_compatibility(invalid_birthdate, fio1, birthdate2, fio2)
    print(f"Результат с некорректной датой: {invalid_result}")

async def test_interpretation_integration():
    """
    Тестирование интеграции с внешним сервисом
    Для этого нужно импортировать и использовать interpret_updated.py
    """
    print("\n=== Для тестирования интеграции импортируйте и используйте interpret_updated.py ===")
    print("Пример использования:")
    print("""
    from interpret_updated import send_to_n8n_for_interpretation
    
    # Получение расчетов
    numerology_data = calculate_numerology_advanced("09.12.2002", "Иванов Иван Иванович")
    
    # Отправка на интерпретацию
    interpretation = await send_to_n8n_for_interpretation(numerology_data, "full")
    
    # Проверка результатов
    print(interpretation)
    """)

async def main():
    """Главная функция для запуска всех тестов"""
    print("Запуск тестирования обновленного модуля нумерологических расчетов...")
    
    await test_single_calculation()
    await test_compatibility_calculation()
    await test_interpretation_integration()
    
    print("\nТестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main())