#!/bin/bash
# Скрипт для тестирования функциональности бота

# Путь к директории проекта
PROJECT_DIR="$(dirname "$(readlink -f "$0")")"
PYTHON_PATH="$(which python3)"

echo "=== Начало тестирования бота ИИ-Нумеролог ==="
echo "Директория проекта: $PROJECT_DIR"

# Проверка наличия необходимых файлов
echo -e "\n=== Проверка наличия необходимых файлов ==="
FILES_TO_CHECK=(
    "bot.py"
    "numerology_core.py"
    "interpret.py"
    "database_sqlite.py"
    "payment_webhook_yukassa.py"
    "weekly_forecast.py"
    "pdf_generator.py"
    "pdf_template.html"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$PROJECT_DIR/$file" ]; then
        echo "✅ Файл $file найден"
    else
        echo "❌ Файл $file не найден"
    fi
done

# Проверка наличия директории для PDF
if [ -d "$PROJECT_DIR/pdfs" ]; then
    echo "✅ Директория pdfs найдена"
else
    echo "❌ Директория pdfs не найдена"
    mkdir -p "$PROJECT_DIR/pdfs"
    echo "✅ Директория pdfs создана"
fi

# Проверка зависимостей
echo -e "\n=== Проверка зависимостей ==="
$PYTHON_PATH -m pip install -r "$PROJECT_DIR/requirements.txt"

# Добавление новых зависимостей для ЮKassa
echo -e "\n=== Добавление зависимостей для ЮKassa ==="
$PYTHON_PATH -m pip install yookassa

# Проверка базы данных
echo -e "\n=== Проверка базы данных ==="
if [ -f "$PROJECT_DIR/numerology_bot.db" ]; then
    echo "✅ База данных найдена"
else
    echo "❌ База данных не найдена"
    echo "Создание новой базы данных..."
    $PYTHON_PATH -c "from database_sqlite import Database; import asyncio; asyncio.run(Database().init())"
    echo "✅ База данных создана"
fi

# Тестирование модуля нумерологических расчетов
echo -e "\n=== Тестирование модуля нумерологических расчетов ==="
$PYTHON_PATH -c "
from numerology_core import calculate_numerology
result = calculate_numerology('1990-01-01', 'Иванов Иван Иванович')
print('Результат расчета:')
for key, value in result.items():
    if key != 'pythagoras_matrix':
        print(f'{key}: {value}')
    else:
        print(f'{key}: {dict(value)}')
"

# Тестирование модуля интерпретации
echo -e "\n=== Тестирование модуля интерпретации ==="
$PYTHON_PATH -c "
import asyncio
from interpret import send_to_n8n_for_interpretation
from numerology_core import calculate_numerology

async def test_interpret():
    result = calculate_numerology('1990-01-01', 'Иванов Иван Иванович')
    interpretation = await send_to_n8n_for_interpretation(result, 'mini')
    print('Результат интерпретации:')
    print(interpretation)

asyncio.run(test_interpret())
"

# Тестирование генерации PDF
echo -e "\n=== Тестирование генерации PDF ==="
$PYTHON_PATH -c "
import asyncio
from interpret import send_to_n8n_for_interpretation
from numerology_core import calculate_numerology
import os

try:
    from pdf_generator_simple import generate_pdf
except ImportError:
    try:
        from text_report_generator import generate_pdf
    except ImportError:
        try:
            from pdf_generator import generate_pdf
        except ImportError:
            print('❌ Не удалось импортировать модуль генерации PDF')
            exit(1)

async def test_pdf():
    result = calculate_numerology('1990-01-01', 'Иванов Иван Иванович')
    interpretation = await send_to_n8n_for_interpretation(result, 'full')
    
    user = {
        'id': 1,
        'tg_id': 123456789,
        'fio': 'Иванов Иван Иванович',
        'birthdate': '1990-01-01'
    }
    
    pdf_path = generate_pdf(user, result, interpretation.get('full_report', {}))
    
    if pdf_path and os.path.exists(pdf_path):
        print(f'✅ PDF успешно сгенерирован: {pdf_path}')
    else:
        print('❌ Ошибка при генерации PDF')

asyncio.run(test_pdf())
"

# Тестирование еженедельного прогноза
echo -e "\n=== Тестирование еженедельного прогноза ==="
$PYTHON_PATH -c "
import asyncio
from weekly_forecast import generate_weekly_forecast

async def test_forecast():
    user_data = {
        'user_id': 1,
        'tg_id': 123456789,
        'fio': 'Иванов Иван Иванович',
        'birthdate': '1990-01-01'
    }
    
    forecast = await generate_weekly_forecast(user_data)
    print('Результат генерации прогноза:')
    print(forecast)

asyncio.run(test_forecast())
"

echo -e "\n=== Тестирование завершено ==="
echo "Для запуска бота выполните: python3 $PROJECT_DIR/bot.py"
echo "Для настройки еженедельных прогнозов выполните: bash $PROJECT_DIR/setup_weekly_forecast.sh"
