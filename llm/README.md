# 🧠 LLM Sentiment Analysis Service

Микросервис количественного анализа сентимента новостей криптовалютного рынка на базе современных LLM с гарантированным извлечением структурированных данных (Pydantic / OpenAI Structured Outputs).

---

## 📁 Структура пакета

```text
llm/
├── sql/                             # Внешние SQL-запросы сервиса
│   ├── fetch_unprocessed_batch.sql  # Выборка пачки необработанных новостей
│   ├── save_llm_result.sql          # Сохранение сентимента и обновление флага processed
│   └── get_table_stats.sql          # Получение общей статистики по таблице
├── main.py                  # Точка входа с обработкой сигналов завершения
├── analyzer.py              # LLM-клиент с обработкой <think> тегов и fallback
├── worker.py                # Демон пакетной обработки с Semaphore
├── db.py                    # Асинхронный пул соединений PostgreSQL (psycopg3 + dict_row)
├── schema.py                # Pydantic-модели и Enum'ы сентимента
├── prompt.py                # Системный промпт финансового аналитика и шаблонизатор
├── config.py                # Pydantic Settings конфигурация сервиса
├── queries.py               # Загрузчик внешних .sql файлов
├── __init__.py
├── Dockerfile                       # Многослойная сборка на базе python:3.12-slim + uv
├── .dockerignore
├── .env.example                     # Шаблоны настроек для Ollama, DeepSeek и OpenAI
├── pyproject.toml                   # Зависимости и конфигурация проекта
└── uv.lock                          # Зафиксированные версии пакетов
```

---

## ⚙️ Логика обработки рассуждений DeepSeek-R1

Модели класса DeepSeek-R1 выводят процесс мышления внутри тегов `<think>...</think>`.  
Модуль `SentimentAnalyzer` ([`analyzer.py`](file:///Users/isnov/git/news-analysis/llm/analyzer.py)) реализует двухконтурную схему:

1. **Контур 1 (Structured Outputs API):**  
   Запрос отправляется через `client.beta.chat.completions.parse()` со строгой схемой `response_format=SentimentAnalysisResult`.  
   Если модель возвращает рассуждения в отдельном поле сообщения (`message.reasoning`), они автоматически переносятся в поле `reasoning` финального объекта.

2. **Контур 2 (Robust Regex Fallback):**  
   Если шлюз модели возвращает сырой текст с тегами `<think>`, включается резервный парсер:
   * Блоки `<think>.*?</think>` вырезаются скомпилированным регулярным выражением `THINK_TAG_REGEX`.
   * Из оставшегося текста извлекается валидный JSON-блок через `JSON_CODEBLOCK_REGEX` или поиск граничных фигурных скобок `{...}`.
   * Выполняется строгая валидация `SentimentAnalysisResult.model_validate_json(clean_json)`.

---

## 🚀 Локальный запуск и разработка

Управление зависимостями осуществляется через менеджер `uv`:

```bash
# Установка виртуального окружения и зависимостей
uv sync

# Запуск сервиса
uv run python main.py
```

Или из корня репозитория:
```bash
make llm-run
```
