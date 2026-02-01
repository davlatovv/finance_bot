# 💰 Finance Bot

Telegram-бот для учёта доходов и расходов с голосовым вводом и AI-категоризацией.

## ✨ Возможности

- 📝 **Добавление записей** — текстом или голосом
- 🎤 **Распознавание речи** — локальный Whisper
- 🤖 **AI-категоризация** — автоматическое определение категории через LLM
- 📂 **Управление категориями** — создание, редактирование, удаление
- 📊 **Отчёты** — статистика по месяцам с разбивкой по категориям
- 🔐 **Безопасность** — rate limiting, валидация, защита от инъекций

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
cd finance_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

### 2. Установка ffmpeg (для Whisper)

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

### 3. Настройка переменных окружения

Создайте файл `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=arcee-ai/trinity-large-preview:free
WHISPER_MODEL=turbo
```

### 4. Запуск

```bash
python bot.py
```

## 🐳 Docker Deployment

Для деплоя на сервере используйте Docker:

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/finance_bot.git
cd finance_bot

# Настроить переменные окружения
cp .env.example .env
nano .env  # Заполнить BOT_TOKEN и OPENROUTER_API_KEY

# Запустить через Docker Compose
docker compose up -d
```

Подробная инструкция: [DEPLOYMENT.md](DEPLOYMENT.md)

## 📱 Использование

1. Отправьте `/start` боту
2. Нажмите **➕ Добавить**
3. Выберите тип: доход или расход
4. Напишите текстом или отправьте голосовое:
   - «Зарплата 50000»
   - «Потратил 500 на кофе»
   - «Купил продукты на 2к»

Бот автоматически определит категорию и запишет транзакцию.

## 🗂 Структура проекта

```
finance_bot/
├── bot.py              # Точка входа
├── config/             # Конфигурация
├── docs/               # Документация
├── src/
│   ├── db/             # База данных (SQLite)
│   ├── handlers/       # Обработчики Telegram
│   ├── keyboards/      # Inline-клавиатуры
│   ├── lexicon/        # Тексты бота
│   ├── llm/            # Интеграция с LLM
│   ├── security/       # Безопасность
│   ├── services/       # Бизнес-логика
│   └── states/         # FSM состояния
└── requirements/       # Зависимости
```

## 🔧 Технологии

- **Python 3.9+**
- **aiogram 3** — Telegram Bot API
- **aiosqlite** — асинхронная работа с SQLite
- **Whisper** — распознавание речи (локально)
- **OpenRouter** — LLM для категоризации

## 📊 База данных

- **users** — пользователи
- **categories** — категории доходов/расходов
- **transactions** — записи транзакций

Данные хранятся 6 месяцев, затем автоматически удаляются.

## 🔐 Безопасность

- Rate limiting (20 сообщений/мин)
- Валидация всех входных данных
- Защита от prompt injection
- Логирование подозрительной активности

## 📖 Документация

- [Архитектура](docs/ARCHITECTURE.md) — описание структуры и компонентов

## 📝 Лицензия

MIT
