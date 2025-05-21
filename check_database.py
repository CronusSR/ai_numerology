# simple_check_db.py
import os
import sqlite3
from datetime import datetime

def check_database():
    """Простая проверка SQLite базы данных без использования класса Database"""
    print("=" * 50)
    print("Проверка базы данных SQLite")
    print("=" * 50)
    
    # Путь к файлу базы данных
    db_file = "numerology_bot.db"
    
    if not os.path.exists(db_file):
        print(f"Ошибка: файл базы данных не найден: {db_file}")
        return
    
    try:
        # Создаем прямое подключение к базе данных
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nТаблицы в базе данных: {[table[0] for table in tables]}")
        
        # Статистика по таблицам
        print("\nСтатистика по таблицам:")
        for table in tables:
            table_name = table[0]
            if table_name == 'sqlite_sequence':  # Пропускаем системную таблицу
                continue
                
            # Количество записей
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  • {table_name}: {count} записей")
        
        # Детальная информация о пользователях
        print("\nПользователи:")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"  • ID: {user['id']}, Telegram ID: {user['tg_id']}, ФИО: {user['fio']}")
            print(f"    Дата рождения: {user['birthdate']}, Язык: {user['lang']}")
            print(f"    Создан: {user['created_at']}")
        
        # Информация о отчетах
        print("\nОтчеты (по типам):")
        cursor.execute("SELECT report_type, COUNT(*) FROM reports GROUP BY report_type")
        report_types = cursor.fetchall()
        for report_type in report_types:
            print(f"  • {report_type[0]}: {report_type[1]} отчетов")
        
        # Последние отчеты
        print("\nПоследние 3 отчета:")
        cursor.execute("SELECT id, user_id, report_type, created_at FROM reports ORDER BY created_at DESC LIMIT 3")
        recent_reports = cursor.fetchall()
        for report in recent_reports:
            print(f"  • ID: {report['id']}, Тип: {report['report_type']}, Дата: {report['created_at']}")
        
        # Информация о размере файла
        size_bytes = os.path.getsize(db_file)
        size_mb = size_bytes / (1024 * 1024)
        print(f"\nРазмер файла базы данных: {size_mb:.2f} МБ")
        print(f"Расположение файла: {os.path.abspath(db_file)}")
        
        # Информация о файле
        file_stats = os.stat(db_file)
        modified_time = datetime.fromtimestamp(file_stats.st_mtime)
        created_time = datetime.fromtimestamp(file_stats.st_ctime)
        print(f"Дата создания: {created_time}")
        print(f"Дата последнего изменения: {modified_time}")
        
        # Проверка целостности базы данных
        print("\nПроверка целостности базы данных...")
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        print(f"Результат проверки: {integrity}")
        
        # Закрываем соединение
        conn.close()
        print("\nПроверка базы данных завершена")
        
    except sqlite3.Error as e:
        print(f"Ошибка SQLite: {e}")
    except Exception as e:
        print(f"Общая ошибка: {e}")

if __name__ == "__main__":
    check_database()