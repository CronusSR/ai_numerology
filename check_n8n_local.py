# check_n8n_connection.py
import requests
import time
import json

def check_local_connection():
    print("Тестирование подключения к localhost...")
    try:
        response = requests.get("http://localhost:5678", timeout=5)
        print(f"Подключение к localhost:5678: {response.status_code}")
    except Exception as e:
        print(f"Ошибка подключения к localhost: {e}")
    
    print("\nТестирование webhook на localhost...")
    try:
        test_data = {"test": True, "report_type": "test"}
        response = requests.post("http://localhost:5678/webhook/c4f6a246-0e5f-4a92-b901-8018c98c11ff", 
                                 json=test_data, timeout=5)
        print(f"Запрос к webhook на localhost: {response.status_code}")
        if response.status_code == 200:
            try:
                print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
            except:
                print(f"Ответ (не JSON): {response.text[:100]}...")
    except Exception as e:
        print(f"Ошибка при запросе к webhook на localhost: {e}")

def check_n8n_connection():
    print("Тестирование подключения к n8n...")
    try:
        response = requests.get("http://n8n:5678", timeout=5)
        print(f"Подключение к n8n:5678: {response.status_code}")
    except Exception as e:
        print(f"Ошибка подключения к n8n: {e}")
    
    print("\nТестирование webhook на n8n...")
    try:
        test_data = {"test": True, "report_type": "test"}
        response = requests.post("http://n8n:5678/webhook/c4f6a246-0e5f-4a92-b901-8018c98c11ff", 
                                 json=test_data, timeout=5)
        print(f"Запрос к webhook на n8n: {response.status_code}")
        if response.status_code == 200:
            try:
                print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
            except:
                print(f"Ответ (не JSON): {response.text[:100]}...")
    except Exception as e:
        print(f"Ошибка при запросе к webhook на n8n: {e}")

if __name__ == "__main__":
    check_local_connection()
    print("\n" + "="*50 + "\n")
    time.sleep(1)
    check_n8n_connection()
    
    print("\nРекомендации:")
    print("1. Если подключение к localhost работает, но к n8n - нет, добавьте запись в файл hosts:")
    print("   127.0.0.1 n8n")
    print("2. Или измените код для использования localhost вместо n8n")
    print("3. Убедитесь, что n8n запущен и доступен")