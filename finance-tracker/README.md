# Finance Tracker

Веб-приложение для учёта личных финансов. Backend предоставляет REST API на FastAPI; в репозитории также есть отдельная HTML-страница в `frontend/index.html`.

## Возможности

- Создание, просмотр и удаление счетов с начальным балансом.
- Учёт доходов и расходов с категорией, датой и комментарием.
- Фильтрация операций и месячные отчёты по доходам, расходам и категориям.
- Сервис уведомлений о тратах от 100 000 ₽: формирует сообщения в памяти, но не отправляет электронную почту.
- Документация API через Swagger UI.

Счета сейчас не содержат отдельного поля валюты. Backend не раздаёт HTML-страницу: frontend и API не объединены общей серверной конфигурацией.

## Требования

- Python 3.13+

Зависимости приложения указаны в `backend/requirements.txt`; версии FastAPI, SQLAlchemy и Pydantic закреплены в этом файле.

## Установка и запуск API

Из корневой папки проекта:

```bash
python -m venv .venv
```

Активируйте виртуальное окружение и установите зависимости:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install -r backend/requirements.txt
```

Запустите сервер из папки `backend`:

```bash
cd backend
uvicorn app.main:app --reload
```

API будет доступен по адресу `http://127.0.0.1:8000`, интерактивная документация — `http://127.0.0.1:8000/docs`. По умолчанию SQLite сохраняет данные в `backend/finance.db`. Путь можно переопределить переменной окружения `DATABASE_URL`.

## API

- `POST`, `GET /api/accounts` — создать счёт и получить список счетов.
- `GET`, `DELETE /api/accounts/{account_id}` — получить или удалить счёт.
- `POST`, `GET /api/operations` — создать операцию или получить список; список поддерживает фильтры `month`, `category`, `type` и `account_id`.
- `GET`, `DELETE /api/operations/{operation_id}` — получить или удалить операцию.
- `GET /api/reports/monthly?month=YYYY-MM` — получить месячный отчёт; доступны необязательные фильтры `category` и `account_id`.
- `GET /health` — проверить состояние сервиса.

## Тесты

Установите зависимости разработки:

```bash
python -m pip install -r backend/requirements-dev.txt
```

Из корневой папки запустите весь набор тестов:

```bash
python -m pytest -c backend/pyproject.toml backend/tests
```

Чтобы сформировать отчёт покрытия:

```bash
python -m pytest -c backend/pyproject.toml --cov=app --cov-report=term-missing backend/tests
```

## Frontend

`frontend/index.html` — отдельная статическая страница. FastAPI не раздаёт её; для совместной работы страницы и API требуется настроить раздачу frontend и проксирование запросов `/api` на backend.
