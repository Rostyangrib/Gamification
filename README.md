# ABAC Auth — FastAPI + React + PostgreSQL

Система авторизации с Attribute-Based Access Control (ABAC). Политики проверяются при логине на основе атрибутов пользователя и контекста (время, выходные и т.д.).

## Структура

```
game_industry/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI приложение
│   │   ├── config.py            # Настройки из .env
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── models/              # User, Policy, AuditLog
│   │   ├── schemas/             # Pydantic v2 схемы
│   │   ├── routers/auth.py      # Эндпоинты авторизации
│   │   ├── services/
│   │   │   ├── abac.py          # ABAC-движок
│   │   │   └── auth.py          # Сервис авторизации
│   │   └── core/
│   │       ├── security.py      # JWT + bcrypt
│   │       └── dependencies.py  # get_current_user
│   ├── alembic/                 # Миграции
│   ├── scripts/seed.py          # Seed-данные
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/LoginPage.tsx
│       ├── pages/WelcomePage.tsx
│       ├── context/AuthContext.tsx
│       └── api/client.ts
├── docker-compose.yml           # backend + frontend (БД — локальный PostgreSQL)
├── backend/Dockerfile
├── frontend/Dockerfile
└── .env.example
```

## Быстрый старт (Docker — рекомендуется)

Требуется **Docker Desktop** и **локальный PostgreSQL** (порт 5432).

Настройки БД по умолчанию (см. `.env`):

| Параметр | Значение |
|----------|----------|
| Host | `localhost` |
| Port | `5432` |
| Database | `postgres` |
| User | `postgres` |
| Password | `1234` |

```bash
# из корня проекта
copy .env.example .env   # Windows; или создайте .env вручную
docker compose up --build -d
```

Backend в Docker подключается к PostgreSQL на вашем компьютере через `host.docker.internal`.

После сборки откройте **http://localhost:5173** (не `0.0.0.0`).

> **Важно:** адрес `http://0.0.0.0:8000` из логов Docker — это служебный адрес сервера внутри контейнера. Браузер его не открывает. Используйте `localhost`.

Проверка сервисов:

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/health |
| PostgreSQL | localhost:5432 (локально, не в Docker) |

Остановить:

```bash
docker compose down
```

Пересобрать после изменений кода:

```bash
docker compose up --build -d
```

Логи:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

---

## Локальный запуск (без Docker)

### 1. PostgreSQL

Убедитесь, что PostgreSQL запущен локально с настройками из `.env`.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy ..\.env.example ..\.env  # или создайте .env вручную
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173

## Тестовые аккаунты (пароль `Test123!`)

| Email | Роль | Отдел | Допуск | Локация | Активен |
|-------|------|-------|--------|---------|---------|
| admin@test.com | ADMIN | IT | 5 | office | ✓ |
| finance@test.com | MANAGER | FINANCE | 4 | office | ✓ |
| hr@test.com | EMPLOYEE | HR | 3 | remote | ✓ |
| dev@test.com | EMPLOYEE | IT | 3 | vpn | ✓ |
| guest@test.com | GUEST | PUBLIC | 0 | remote | ✓ |
| blocked@test.com | EMPLOYEE | IT | 2 | office | ✗ |

## ABAC-политики (login)

1. **DENY** — неактивный аккаунт
2. **DENY** — роль GUEST
3. **DENY** — remote вне 9:00–18:00
4. **DENY** — clearance < 2 в выходные
5. **ALLOW** — все остальные

## API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/auth/register | Регистрация |
| POST | /api/auth/login | Вход (+ ABAC) |
| POST | /api/auth/logout | Выход |
| GET | /api/auth/me | Текущий пользователь |
| POST | /api/auth/check | Проверка доступа без пароля |

При DENY на login возвращается `403` с телом:
```json
{"detail": "Вход запрещён", "reason": "..."}
```
