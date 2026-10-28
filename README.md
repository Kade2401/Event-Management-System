# Event Management System

Веб-приложение на **Django** для создания, организации и управления мероприятиями с интерактивной картой, системой ролей участников и приглашениями по QR-коду.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2%2B%20%7C%206.0-092E20?logo=django&logoColor=white)
![SQLite / PostgreSQL](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-336791?logo=postgresql&logoColor=white)

---

## Основные возможности

- **Управление событиями (CRUD):** создание, редактирование и удаление мероприятий с указанием даты, времени, описания и лимита мест.
- **Типы видимости событий:**
  - 👤 **Normal** — личные события организатора.
  - 🔒 **Private (Invite-only)** — закрытые мероприятия с генерацией персональной ссылки и **QR-кода** для быстрой регистрации гостей.
  - 🌍 **Global** — публичные события, открытые для всех пользователей (создаются администраторами и группой `globals`).
- **Интерактивные карты (Leaflet + OpenStreetMap):** выбор локации на карте с автоматическим определением адреса (Reverse Geocoding) и отображение всех доступных ивентов на карте в профиле пользователя.
- **Управление участниками:** добавление участников, назначение и редактирование их ролей (`VIP`, `speaker`, `guest` и др.), контроль свободных мест.
- **Фильтрация и сортировка:** поиск событий по диапазону дат, наличию свободных мест и сортировка по дате или алфавиту.
- **Личный кабинет:** регистрация, авторизация, просмотр карты своих мероприятий и управление аккаунтом.

---

## Технологический стек

- **Backend:** Python, Django, Django REST Framework, Gunicorn, WhiteNoise
- **База данных:** SQLite (по умолчанию для разработки) / PostgreSQL (через `DATABASE_URL`)
- **Frontend:** HTML5, CSS3 (Glassmorphism UI), JavaScript, Leaflet.js, Font Awesome

---

## Быстрый старт и установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/Kade2401/Event-Management-System.git
cd Event-Management-System
```

### 2. Создание и активация виртуального окружения
**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Применение миграций базы данных
```bash
python manage.py migrate
```

### 5. Создание суперпользователя (опционально)
Для доступа к админ-панели (`/admin/`) и создания глобальных событий:
```bash
python manage.py createsuperuser
```

### 6. Запуск сервера разработки
```bash
python manage.py runserver
```
После запуска откройте в браузере: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## Запуск тестов

Для проверки корректности работы приложения выполните:
```bash
python manage.py check
python manage.py test
```

---

## Структура проекта

```text
Event-Management-System/
├── DjangoProject1/      # Настройки проекта (settings, urls, wsgi/asgi)
├── events/              # Основное приложение (модели, views, формы, тесты, миграции)
├── templates/           # HTML-шаблоны страниц и авторизации
├── static/              # Стили (CSS) и статические ресурсы
├── manage.py            # Точка входа для команд Django
└── requirements.txt     # Зависимости проекта
```
