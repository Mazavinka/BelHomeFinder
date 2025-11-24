<h1 align="center">🏡 BelHomeFinder</h1>

<p align="center">
Асинхронный Telegram-бот для поиска квартир в долгосрочную аренду в Беларуси  
</p>

<p align="center">
<img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge">
<img src="https://img.shields.io/badge/Aiogram-3.x-yellow?style=for-the-badge">
<img src="https://img.shields.io/badge/Tortoise%20ORM-async%20ORM-green?style=for-the-badge">
<img src="https://img.shields.io/badge/Asyncio-Enabled-orange?style=for-the-badge">
<img src="https://img.shields.io/badge/Docker-Ready-lightblue?style=for-the-badge">
<img src="https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge">
</p>

---

# 📌 Описание проекта

**BelHomeFinder** — это интеллектуальная система, которая автоматически:

🔍 парсит объявления о сдаче жилья с **Kufar**  
📡 отслеживает новые предложения в реальном времени  
📍 определяет район квартиры по координатам (*GeoJSON + Shapely*)  
🗺 ищет ближайшие POI по данным **OpenStreetMap / Osmium**  
🤖 отправляет пользователю только подходящие объявления  

Проект полностью асинхронный:  
парсер → события → база → очередь → Telegram-бот.

Сервис работает **24/7**, устойчив к ошибкам и развёрнут в Docker.


---

# ✨ Основной функционал

### 🏙 Фильтры
- город  
- район  
- количество комнат  
- минимальная / максимальная цена  

### 📬 Уведомления
- мгновенная отправка новых объявлений  
- медиагруппы до 10 изображений  
- обработка FloodWait  
- отправка последних 5 объявлений новым пользователям  

### 🗺 Геолокация
- определение района по GeoJSON  
- определение инфраструктуры в радиусе 500 м:
  - метро  
  - аптеки  
  - магазины  
  - школы  
  - детсады  
  - банки  

### 🧠 Логика сервиса
- очередь `asyncio.Queue`  
- ORM-сигналы `tortoise.signals`  
- фильтрация по параметрам  
- кеширование POI при старте  


---

# 🧩 Технологии

| Компонент | Технологии |
|----------|------------|
| Telegram | Aiogram 3 |
| База данных | **Tortoise ORM** (SQLite / PostgreSQL) |
| Парсинг | aiohttp |
| Асинхронность | asyncio |
| Геоданные | Osmium, Shapely, GeoJSON |
| Очереди | asyncio.Queue + Tortoise ORM signals |
| Логирование | logging + RotatingFileHandler |
| Развёртывание | Docker / Docker Compose |
| Конфигурация | python-dotenv |

---

# 🧠 Архитектура
## Общая архитектура проекта:
```mermaid
flowchart LR
    A[Парсер Kufar] -->|Новые объявления| B[(База Tortoise ORM)]
    B -->|post_save SIGNAL| C[Очередь постов]
    C --> D[Обработчик новых объявлений]
    D -->|Рассылка| E[Telegram Bot]

    E -->|Сохранение настроек| B
    E --> F[FSM / UI логика]
```
##  Цикл работы Telegram-бота:
```mermaid
sequenceDiagram
    participant U as User
    participant T as TelegramBot
    participant DB as DB (Tortoise ORM)

    U->>T: /start
    T->>DB: get_or_create_user()
    T->>U: Приветственное сообщение

    U->>T: Выбор фильтров
    T->>DB: update user settings

    DB-->>T: SIGNAL user.is_active == True
    T->>U: Отправка 5 свежих объявлений
```
##  Процесс парсинга:
```mermaid
flowchart TD
    A1[Запуск парсера] --> B1[Запрос в API Kufar]
    B1 --> C1[Разбор объявления]
    C1 --> D1[Определение района GeoJSON]
    D1 --> E1[Поиск POI OSM]
    E1 --> F1[(Сохранение в БД Tortoise)]

    F1 -->|post_save SIGNAL| G1[Очередь новых постов]
    G1 --> H1[Рассылка пользователям]
```


# 🚀 Установка и запуск BelHomeFinder

Ниже приведена подробная инструкция по установке и запуску проекта для **Linux**, **Windows** и **Docker**.

---

# ⚙ Требования

- Python **3.11+**
- pip
- virtualenv (рекомендуется)
- Git
- (опционально) Docker + Docker Compose


База настраивается через `DB_PATH` в `.env`.
Поддержка  **PostgreSQL**.

---

# 🐧 Установка на Linux

### 1. Установите зависимости

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

### 2. Клонируйте репозиторий

```bash
git clone https://github.com/USERNAME/BelHomeFinder.git
cd BelHomeFinder
```

### 3. Создайте виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Установите зависимости

```bash
pip install -r requirements.txt
```

### 5. Создайте файл `.env`

Пример:

```
TG_BOT_TOKEN=ваш_токен_бота
DB_PATH=database.db
MAX_PRICE_UNLIMITED=20000
```

### 6. Запуск проекта

```bash
python main.py
```

---

# 🪟 Установка на Windows

### 1. Клонируйте проект

```
git clone https://github.com/USERNAME/BelHomeFinder.git
cd BelHomeFinder
```

### 2. Создайте виртуальное окружение

```
python -m venv venv
venv\Scripts\activate
```

### 3. Установите зависимости

```
pip install -r requirements.txt
```

### 4. Создайте файл `.env`

```
TG_BOT_TOKEN=ваш_токен_бота
DB_PATH=./database.db
MAX_PRICE_UNLIMITED=20000
```

### 5. Запуск

```
python main.py
```

---

# 🐳 Запуск через Docker

## 1️⃣ Собрать Docker-образ

```bash
docker build -t belhomefinder .
```

## 2️⃣ Запустить контейнер

```bash
docker run -d \
    --name belhomefinder \
    --env-file .env \
    -v $(pwd)/database.db:/app/database.db \
    belhomefinder
```

---

# 🧱 Docker Compose (рекомендуемый способ)

Создайте файл:

```
docker-compose.yml
```

И добавьте:

```yaml
version: '3.8'

services:
  belhomefinder:
    build: .
    container_name: belhomefinder
    restart: always
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./geo:/app/geo
```

Запуск:

```bash
docker compose up -d
```

---

# ✔ **Пример .env**

```
TG_BOT_TOKEN=ваш_telegram_токен
DB_PATH=postgres://user:password@host:5432/dbname
MAX_PRICE_UNLIMITED=20000
```

---

# 🔎 Проверка, что всё работает

Если бот запустился успешно, ты увидишь в логах:

```
Parser has been started
Bot polling started
```

---

# 🧰 Полезные команды

Остановить Docker-контейнер:

```bash
docker stop belhomefinder
```

Удалить:

```bash
docker rm belhomefinder
```

Пересобрать:

```bash
docker compose build --no-cache
```

---


# 🧪 Roadmap

- [x] Перенос БД на PostgreSQL  
- [ ] Админ-панель  
- [ ] Caching POI  
- [ ] ML-оценка объявлений  
- [ ] Web-интерфейс  
- [ ] GitHub Actions авто-деплой  

