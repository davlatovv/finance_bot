# 🐳 Деплой Finance Bot на сервере

Инструкция по развёртыванию Telegram-бота для учёта финансов на сервере с использованием Docker.

## 📋 Требования

### Минимальные системные требования:
- **ОС:** Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- **RAM:** 512 MB (рекомендуется 1 GB)
- **Диск:** 2 GB свободного места
- **CPU:** 1 ядро

### Установленное ПО:
- Docker 20.10+
- Docker Compose 2.0+
- Git

## 🚀 Быстрый старт

### 1. Установка Docker (если не установлен)

**Ubuntu/Debian:**
```bash
# Обновить пакеты
sudo apt-get update

# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установить Docker Compose
sudo apt-get install docker-compose-plugin

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

**Проверка установки:**
```bash
docker --version
docker compose version
```

### 2. Клонирование репозитория

```bash
# Клонировать проект
git clone https://github.com/yourusername/finance_bot.git
cd finance_bot
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
nano .env
```

Добавьте следующие переменные:

```env
# Telegram Bot Token (получить от @BotFather)
BOT_TOKEN=your_telegram_bot_token_here

# OpenRouter API Key (получить на openrouter.ai)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Модель LLM (опционально, по умолчанию используется бесплатная)
OPENROUTER_MODEL=arcee-ai/trinity-large-preview:free

# Модель Whisper (опционально, по умолчанию turbo)
WHISPER_MODEL=turbo
```

**Сохраните файл:** `Ctrl+O`, `Enter`, `Ctrl+X`

> [!IMPORTANT]
> Никогда не коммитьте файл `.env` в Git! Он уже добавлен в `.gitignore`.

### 4. Создание директории для данных

```bash
mkdir -p data
chmod 755 data
```

### 5. Запуск бота

**Собрать и запустить:**
```bash
docker compose up -d
```

**Проверить статус:**
```bash
docker compose ps
```

**Просмотр логов:**
```bash
docker compose logs -f
```

## 📊 Управление

### Основные команды

**Остановить бота:**
```bash
docker compose stop
```

**Запустить бота:**
```bash
docker compose start
```

**Перезапустить бота:**
```bash
docker compose restart
```

**Полностью остановить и удалить контейнер:**
```bash
docker compose down
```

**Просмотр логов (последние 100 строк):**
```bash
docker compose logs --tail=100
```

**Просмотр логов в реальном времени:**
```bash
docker compose logs -f
```

**Войти в контейнер (для отладки):**
```bash
docker compose exec finance-bot /bin/bash
```

### Проверка здоровья бота

```bash
docker compose ps
```

Статус должен быть `healthy` или `running`.

## 🔄 Обновление бота

### Обновление кода:

```bash
# Остановить бота
docker compose down

# Получить обновления
git pull

# Пересобрать образ
docker compose build

# Запустить бота
docker compose up -d
```

### Обновление только конфигурации:

```bash
# Отредактировать .env
nano .env

# Перезапустить
docker compose restart
```

## 💾 Резервное копирование

### Создание бэкапа базы данных:

```bash
# Копировать БД
cp data/finance.db backup/finance_$(date +%Y%m%d_%H%M%S).db

# Или создать tar архив
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/
```

### Восстановление из бэкапа:

```bash
# Остановить бота
docker compose stop

# Восстановить БД
cp backup/finance_20260131_120000.db data/finance.db

# Запустить бота
docker compose start
```

### Автоматический бэкап (cron):

```bash
# Редактировать crontab
crontab -e

# Добавить задачу (каждый день в 03:00)
0 3 * * * cd /path/to/finance_bot && cp data/finance.db backup/finance_$(date +\%Y\%m\%d).db
```

## 🔍 Мониторинг

### Проверка использования ресурсов:

```bash
docker stats finance-bot
```

### Проверка логов на ошибки:

```bash
docker compose logs | grep -i error
```

### Проверка размера базы данных:

```bash
ls -lh data/finance.db
```

## 🐛 Устранение проблем

### Бот не запускается

**Проверьте логи:**
```bash
docker compose logs
```

**Проверьте переменные окружения:**
```bash
docker compose config
```

### Ошибки с правами доступа

```bash
# Исправить права на директорию data
sudo chown -R 1000:1000 data/
```

### Контейнер постоянно перезапускается

```bash
# Проверить health check
docker inspect finance-bot | grep -A 10 Health

# Посмотреть последние логи
docker compose logs --tail=50
```

### Очистка места на диске

```bash
# Удалить неиспользуемые образы
docker image prune -a

# Удалить все неиспользуемые ресурсы
docker system prune -a --volumes
```

## 🔒 Безопасность

### Рекомендации:

1. **Файрвол:** Настройте UFW или iptables
   ```bash
   # Разрешить только SSH
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

2. **Регулярные обновления:**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

3. **Ограничение доступа к .env:**
   ```bash
   chmod 600 .env
   ```

4. **Мониторинг логов:**
   Регулярно проверяйте логи на подозрительную активность

5. **SSL для веб-хуков (если используете):**
   Используйте Let's Encrypt для SSL сертификатов

## 📈 Оптимизация производительности

### Уменьшение использования памяти:

Отредактируйте `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # Уменьшить до 512MB
```

### Использование более легкой модели Whisper:

В `.env`:
```env
WHISPER_MODEL=base  # Вместо turbo
```

## 📝 Структура проекта на сервере

```
/opt/finance_bot/          # Рекомендуемое расположение
├── .env                   # Переменные окружения (не в Git!)
├── docker-compose.yml     # Orchestration
├── Dockerfile
├── bot.py
├── config/
├── src/
├── data/                  # Персистентные данные
│   └── finance.db        # SQLite база
├── backup/               # Бэкапы (создать вручную)
└── logs/                 # Логи (опционально)
```

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs`
2. Проверьте статус: `docker compose ps`
3. Перезапустите: `docker compose restart`
4. Пересоберите: `docker compose up -d --build`

## 📌 Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [OpenRouter API](https://openrouter.ai/)

---

**Готово!** 🎉 Ваш бот работает на сервере в Docker-контейнере.
