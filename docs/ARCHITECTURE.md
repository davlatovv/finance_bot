# Архитектура Finance Bot

## Обзор

Finance Bot — Telegram-бот для учёта доходов и расходов с голосовым вводом и AI-категоризацией.

## Структура проекта

```
finance_bot/
├── bot.py                 # Точка входа
├── config/               
│   ├── base.py            # Утилиты конфигурации
│   └── config.py          # Загрузка настроек из .env
├── data/                  # База данных и временные файлы
│   ├── finance_bot.db     # SQLite база данных
│   └── temp_audio/        # Временные аудиофайлы
├── docs/                  # Документация
├── requirements/          # Зависимости
└── src/
    ├── db/                # Работа с базой данных
    │   ├── database.py    # Класс Database (aiosqlite)
    │   └── models.py      # Модели данных (dataclasses)
    ├── handlers/          # Обработчики Telegram
    │   ├── start.py       # /start и главное меню
    │   ├── transactions.py # Добавление транзакций
    │   ├── categories.py  # Управление категориями
    │   └── reports.py     # Отчёты
    ├── keyboards/         # Inline-клавиатуры
    ├── lexicon/           # Тексты бота
    ├── llm/               # Интеграция с LLM
    │   ├── prompts.py     # Системные промпты
    │   └── tools.py       # Tool definitions для function calling
    ├── security/          # Безопасность
    │   ├── rate_limiter.py # Rate limiting
    │   └── validators.py  # Валидация входных данных
    ├── services/          # Бизнес-логика
    │   ├── whisper_service.py # Распознавание речи
    │   ├── llm_service.py     # Обработка через LLM
    │   └── transaction_service.py # Транзакции
    └── states/            # FSM состояния
```

## Слои приложения

### 1. Handlers (Представление)
- Обрабатывают входящие сообщения и callback'и
- Управляют FSM-состояниями
- Делегируют бизнес-логику сервисам

### 2. Services (Бизнес-логика)
- `WhisperService` — распознавание речи
- `LLMService` — обработка текста через AI
- `TransactionService` — операции с транзакциями

### 3. Database (Данные)
- `Database` — асинхронная работа с SQLite
- Модели: `User`, `Category`, `Transaction`

### 4. Security (Безопасность)
- Rate limiting через middleware
- Валидация всех входных данных
- Защита от prompt injection

## Схема базы данных

```sql
-- Пользователи
users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
    created_at TIMESTAMP
)

-- Категории
categories (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name TEXT,
    type TEXT CHECK (type IN ('income', 'expense')),
    created_at TIMESTAMP,
    UNIQUE (user_id, name, type)
)

-- Транзакции
transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    category_id INTEGER REFERENCES categories(id),
    amount REAL CHECK (amount > 0),
    type TEXT CHECK (type IN ('income', 'expense')),
    description TEXT,
    raw_text TEXT,
    created_at TIMESTAMP
)
```

### Индексы
- `idx_users_telegram_id` — быстрый поиск по Telegram ID
- `idx_transactions_user_date` — отчёты по периодам

## Поток данных

### Добавление транзакции (текст)
```
User → Telegram → Handler → LLMService → Database
                              ↓
                         OpenRouter API
```

### Добавление транзакции (голос)
```
User → Telegram → Handler → WhisperService → LLMService → Database
                              ↓                 ↓
                         Whisper (local)   OpenRouter API
```

## Формат ответа LLM

LLM использует function calling с двумя инструментами:

### create_category
```json
{
  "name": "Продукты",
  "type": "expense"
}
```

### create_transaction
```json
{
  "amount": 500.0,
  "type": "expense",
  "category_name": "Продукты",
  "description": "Покупки в магазине"
}
```

## Безопасность

1. **Rate Limiting**
   - 20 сообщений/минуту
   - 30 callback'ов/минуту
   - 5 голосовых/минуту
   - 60 сек cooldown при превышении

2. **Валидация**
   - Макс. длина текста: 500 символов
   - Макс. длина голосового: 5 минут
   - Макс. размер файла: 25 МБ
   - Макс. сумма: 10 000 000 ₽

3. **Prompt Injection Protection**
   - Санитизация входных данных
   - Логирование подозрительных паттернов

## Автоочистка данных

Транзакции старше 6 месяцев автоматически удаляются при запуске бота.

## Масштабирование

Для масштабирования рекомендуется:
- Redis для FSM storage
- PostgreSQL вместо SQLite
- Celery для очередей Whisper/LLM задач
- Kubernetes для горизонтального масштабирования
