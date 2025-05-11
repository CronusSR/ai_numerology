# check_external_webhook.py
import requests
import json

def check_webhook_connection():
    webhook_url = "https://nnikochann.ru/webhook/numero_post_bot"
    
    print(f"Тестирование подключения к внешнему webhook: {webhook_url}")
    
    # Тестовые данные
    test_data = {
        "report_type": "test",
        "life_path": 3,
        "expression": 6,
        "soul_urge": 7,
        "personality": 8,
        "test": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(webhook_url, json=test_data, headers=headers, timeout=10)
        
        print(f"Статус: {response.status_code}")
        print(f"Заголовки: {response.headers}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"JSON ответ: {json.dumps(json_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"Текст ответа: {response.text[:500]}")
        else:
            print(f"Ошибка: {response.text[:500]}")
    except Exception as e:
        print(f"Ошибка при подключении: {e}")

if __name__ == "__main__":
    check_webhook_connection()