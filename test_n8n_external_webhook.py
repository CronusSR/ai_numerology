# test_n8n_external_webhook.py
import requests
import json

# URL вашего webhook в n8n
n8n_webhook_url = "http://localhost:5678/webhook/c4f6a246-0e5f-4a92-b901-8018c98c11ff"

# Тестовые данные
test_data = {
    "report_type": "mini",
    "life_path": 3,
    "expression": 6,
    "soul_urge": 7,
    "personality": 8
}

# Отправка запроса
response = requests.post(n8n_webhook_url, json=test_data)

# Вывод результатов
print(f"Статус: {response.status_code}")
try:
    print(f"Ответ: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
except:
    print(f"Текст ответа: {response.text}")