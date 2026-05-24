# Backend — Proxy Access API

FastAPI-сервис, реализующий бизнес-логику проекта: аутентификация, выдача и активация ключей, управление пулом виртуальных машин, realtime-мониторинг подключений, админ-CRUD.

---

## Содержание

- [Стек](#стек)
- [Структура](#структура)
- [Локальный запуск без Docker](#локальный-запуск-без-docker)
- [Переменные окружения](#переменные-окружения)
- [API](#api)
  - [Auth](#auth)
  - [Profile](#profile)
  - [Activation](#activation)
  - [User VMs](#user-vms)
  - [Admin VMs](#admin-vms)
  - [WebSocket](#websocket)
  - [Health](#health)
- [Модель данных](#модель-данных)
- [Безопасность](#безопасность)
- [Celery](#celery)
- [Rate limiting](#rate-limiting)
- [Тесты](#тесты)
- [Troubleshooting](#troubleshooting)

---

## Стек

| Компонент | Версия | Назначение |
|---|---|---|
| Python | 3.12 | runtime |
| FastAPI | 0.136 | веб-фреймворк |
| SQLAlchemy | 2.0 | ORM (sync API + `Mapped[...]` declarative) |
| Pydantic | 2.13 | валидация + сериализация |
| python-jose | 3.5 | JWT |
| passlib + bcrypt | 1.7 + 4.0 | хеширование паролей |
| psycopg2-binary | 2.9 | драйвер PostgreSQL |
| Celery | 5.6 | фоновые задачи (email) |
| Redis | 7.4 (client) | брокер Celery + rate-limit storage |
| slowapi | 0.1.9 | rate limiting |

---

## Структура

```
Backend/
├── app/
│   ├── core/
│   │   ├── config.py          Pydantic Settings — все env-переменные
│   │   ├── security.py        bcrypt, JWT (create/decode), generate_activation_key
│   │   ├── dependencies.py    get_current_user, get_current_active_user, get_current_admin
│   │   ├── rate_limit.py      slowapi Limiter с Redis-storage
│   │   └── celery_app.py      Celery instance (broker + backend = Redis)
│   ├── db/
│   │   ├── database.py        engine, SessionLocal
│   │   ├── deps.py            FastAPI dependency get_db
│   │   ├── models.py          Admin, User, VirtualMachine, ProxyProtocol enum
│   │   ├── init_db.py         create_all + seed_admin (entrypoint при старте контейнера)
│   │   └── seed.py            seed_admin() — создаёт админа из ENV если его нет
│   ├── routers/
│   │   ├── auth.py            /auth/* (register, login, refresh, token, admin/login)
│   │   ├── profile.py         /profile/* (get, refresh-key, change-password)
│   │   ├── activation.py      /api/activate-key
│   │   ├── user_vms.py        /api/virtual-machines, /api/connect, /api/disconnect
│   │   ├── admin_vms.py       /admin/virtual-machines/* (CRUD)
│   │   └── ws.py              /ws/connection-status (WebSocket)
│   ├── schemas/
│   │   ├── auth.py            UserRegisterRequest, UserLoginRequest, TokenResponse...
│   │   ├── user.py            UserResponse, RefreshKeyResponse, ChangePasswordRequest
│   │   ├── activation.py      ActivationKeyRequest/Response
│   │   └── vm.py              VirtualMachine{Create,Update,Response,Public} + ProxyConnectionResponse
│   ├── services/
│   │   ├── vm_pool.py         ensure_free_vm_or_503 — проверка наличия свободных VM
│   │   └── email_sender.py    SMTP клиент (SSL/STARTTLS auto)
│   ├── tasks/
│   │   ├── activation_keys.py issue_activation_key — генерация ключа + сохранение на user
│   │   └── email.py           Celery task send_activation_key (с retry)
│   └── main.py                FastAPI app + CORS + slowapi middleware
├── tests/                     pytest
├── Dockerfile                 python:3.12-slim, single-stage
├── requirements.txt           prod-зависимости
├── requirements-dev.txt       + pytest, httpx
└── pytest.ini
```

---

## Локальный запуск без Docker

Нужны: Python 3.12+, PostgreSQL 14+, Redis 6+.

```powershell
cd Backend

# 1. Виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Переменные окружения (в Backend\.env или корневом .env)
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/proxy
# REDIS_URL=redis://localhost:6379/0
# JWT_SECRET_KEY=<сильный_секрет>
# ADMIN_EMAIL=admin@example.com
# ADMIN_PASSWORD=...
# SMTP_USER=...
# SMTP_PASSWORD=<gmail-app-password>
# SMTP_FROM_EMAIL=...

# 3. Создать схему и админа
python -m app.db.init_db

# 4. Запустить uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. В отдельном терминале — Celery worker (нужен для отправки email)
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Swagger будет на `http://localhost:8000/docs`.

---

## Переменные окружения

Pydantic Settings читает из переменных окружения и/или из `.env`. Полный список:

| Переменная | Тип | Default | Назначение |
|---|---|---|---|
| `DATABASE_URL` | str | `postgresql://postgres:postgres@localhost:5432/proxy` | Connection string SQLAlchemy |
| `REDIS_URL` | str | `redis://localhost:6379/0` | Celery broker + slowapi storage |
| `JWT_SECRET_KEY` | str | **обязательно** | Подпись JWT (минимум 32 байта) |
| `JWT_ALGORITHM` | str | `HS256` | HS256 / RS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | TTL access |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | `7` | TTL refresh |
| `ACTIVATION_KEY_BYTES` | int | `32` | Байт энтропии в `secrets.token_urlsafe` |
| `ADMIN_EMAIL` | str | _нет_ | Если задан вместе с `ADMIN_PASSWORD` — при старте создаётся админ |
| `ADMIN_PASSWORD` | str | _нет_ | Пароль для seed_admin |
| `SMTP_HOST` | str | `smtp.gmail.com` | |
| `SMTP_PORT` | int | `587` | 465 → SSL, иначе STARTTLS |
| `SMTP_USER` | str | _нет_ | login для SMTP |
| `SMTP_PASSWORD` | str | _нет_ | пароль (для Gmail — App Password) |
| `SMTP_FROM_EMAIL` | str | _нет_ | From-заголовок |
| `RATE_LIMIT_ENABLED` | bool | `true` | Отключение для отладки |
| `RATE_LIMIT_GLOBAL_PER_MINUTE` | int | `120` | Глобальный лимит на IP |
| `DEBUG` | bool | `false` | Включает `echo=True` для SQLAlchemy |

---

## API

Все ответы — JSON. Время — ISO 8601 в UTC (`2026-05-23T12:34:56+00:00`).

### Auth

#### `POST /auth/register`

Регистрация нового пользователя. Перед созданием проверяет наличие свободной VM в пуле — если нет, возвращает `503` и пользователь **не создаётся**.

```json
// Request
{
  "email": "user@example.com",
  "password": "MyStrongPass123",
  "password_confirm": "MyStrongPass123"
}

// 201 Created
{
  "message": "User registered successfully. Activation key email queued."
}

// 400 — пароли не совпадают / email уже занят
// 503 — все прокси заняты, ключ не выдан
```

#### `POST /auth/login`

```json
// Request
{ "email": "user@example.com", "password": "MyStrongPass123" }

// 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}

// 401 — неверные креды
// 403 — is_active=False
```

#### `POST /auth/refresh`

```json
// Request
{ "refresh_token": "eyJ..." }

// 200
{ "access_token": "eyJ...", "token_type": "bearer" }

// 401 — невалидный/просроченный refresh
```

> Внимание: refresh-токен **не ротируется**. См. [P0.4 в README#known-limitations](../README.md#известные-ограничения).

#### `POST /auth/token`

OAuth2-совместимый login для Swagger UI. Принимает `application/x-www-form-urlencoded` с полями `username` (=email) и `password`.

#### `POST /auth/admin/login`

Логин для админа. Возвращает токены со scope `admin_access` / `admin_refresh`.

---

### Profile

Все endpoints требуют `Authorization: Bearer <access_token>`.

#### `GET /profile`

```json
// 200
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "activation_key_expires": "2026-05-30T12:00:00+00:00",
  "created_at": "...",
  "updated_at": "..."
}
```

> **Сам ключ через API не возвращается** — это bearer credential, отдаётся только в email при выдаче.

#### `POST /profile/refresh-key`

Генерирует новый ключ (старый инвалидируется), отправляет на email.

- Если у юзера **уже есть назначенная VM** — проверка пула пропускается (новый ключ может пригодиться для переактивации).
- Если назначенной нет и в пуле тоже свободных нет — **503**.

```json
// 200
{ "activation_key_expires": "...", "message": "Activation key refreshed successfully" }

// 503 — нет свободных VM
```

#### `POST /profile/change-password`

```json
// Request
{ "old_password": "...", "new_password": "...", "new_password_confirm": "..." }

// 200
{ "message": "Password changed successfully" }

// 400 — пароли не совпадают / старый пароль неверен
```

> Существующие JWT после смены пароля **остаются валидными**. Это известное ограничение.

---

### Activation

#### `POST /api/activate-key`

Превращает одноразовый ключ в сессию + назначает VM из пула.

Логика:
1. Найти юзера по `activation_key` (если нет — `400`)
2. Проверить TTL ключа (если истёк — `400`)
3. Если у юзера уже есть назначенная VM — отдать её
4. Иначе атомарно зарезервировать свободную (`SELECT ... FOR UPDATE SKIP LOCKED`)
5. Если свободных нет — **rollback**, `503`. Ключ **остаётся валидным**, можно повторить позже.
6. При успехе — обнулить `activation_key`, выдать access+refresh токены

```json
// Request
{ "activation_key": "abc123..." }

// 200
{
  "status": "activated",
  "user_id": 1,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "vm_id": 5,
  "proxy": { "host": "10.0.0.5", "port": 1080, "protocol": "socks5" }
}

// 400 — Invalid activation key / Activation key expired
// 503 — All proxies are busy (ключ не потребился)
```

---

### User VMs

#### `GET /api/virtual-machines`

Список всех активных VM (без `current_user_id`, только `is_occupied`-флаг).

#### `POST /api/connect`

Если у юзера уже есть назначенная VM — вернёт её. Иначе резервирует свободную (`SELECT FOR UPDATE SKIP LOCKED`).

```json
// 200
{ "status": "connected", "vm_id": 5, "proxy": {...} }

// 503 — All proxies are busy
```

#### `POST /api/disconnect`

Идемпотентно освобождает VM юзера (`current_user_id = NULL`). Если назначенной не было — всё равно `200`.

```json
{ "status": "disconnected", "vm_id": null, "proxy": null }
```

---

### Admin VMs

Все endpoints требуют admin-JWT.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/admin/virtual-machines` | Список всех VM (включая `current_user_id`) |
| `POST` | `/admin/virtual-machines` | Создать VM. `400` при дублирующейся паре `(host, port)` |
| `PATCH` | `/admin/virtual-machines/{vm_id}` | Обновить поля |
| `POST` | `/admin/virtual-machines/{vm_id}/release` | Принудительно освободить (`current_user_id = NULL`) |
| `DELETE` | `/admin/virtual-machines/{vm_id}` | Удалить (204). **Без проверки на активное подключение** |

---

### WebSocket

#### `GET /ws/connection-status?token=<access_token>`

Раз в 3 секунды шлёт JSON с одним из четырёх статусов:

```json
// 1) Юзер подключён к VM
{ "status": "connected", "message": "...", "proxy": { "host": "...", "port": 1080, "protocol": "socks5" } }

// 2) Юзер не подключён, но в пуле есть свободные
{ "status": "disconnected", "message": "User has no active proxy connection" }

// 3) Юзер не подключён, и в пуле нет свободных
{ "status": "no_free_vms", "message": "All proxies are busy" }

// 4) Сбой при чтении из БД (соединение остаётся живым, попытки продолжаются)
{ "status": "error", "message": "Failed to fetch connection status", "detail": "..." }
```

- Невалидный/просроченный токен при handshake → `close(code=4001)`
- Токен проверяется **только при handshake** — это известное ограничение

---

### Health

#### `GET /`

```json
{ "status": "ok" }
```

Простой liveness-пинг (БД/Redis не проверяет).

---

## Модель данных

```
┌────────────────────┐         ┌─────────────────────────┐
│       admins       │         │          users          │
├────────────────────┤         ├─────────────────────────┤
│ id (PK)            │         │ id (PK)                 │
│ email (uniq)       │         │ email (uniq)            │
│ password_hash      │         │ password_hash           │
│ created_at         │         │ is_active               │
│ updated_at         │         │ activation_key (uniq)   │
└────────────────────┘         │ activation_key_expires  │
                               │ created_at, updated_at  │
                               └────────────┬────────────┘
                                            │ 1:N (логически)
                                            │ — но current_user_id UNIQUE,
                                            │   значит фактически 1:1
                                            ▼
                               ┌─────────────────────────┐
                               │    virtual_machines     │
                               ├─────────────────────────┤
                               │ id (PK)                 │
                               │ name                    │
                               │ host, port (uniq pair)  │
                               │ protocol (enum)         │
                               │ is_active               │
                               │ current_user_id (FK, uniq, nullable) │
                               │ last_used_at            │
                               └─────────────────────────┘
```

Enum `ProxyProtocol`: `socks5`, `http`, `https`.

**Ключевая инвариант:** `VirtualMachine.current_user_id` имеет `UNIQUE NULL` ограничение → одна VM = один юзер. Резервирование делается через `SELECT ... FOR UPDATE SKIP LOCKED` для безопасности при параллельных запросах.

---

## Безопасность

### Что реализовано

- bcrypt с дефолтными параметрами passlib (work factor 12)
- JWT через python-jose с HS256
- Раздельные scope-ы для user (`access` / `refresh`) и admin (`admin_access` / `admin_refresh`)
- `SecretStr` для секретов в Pydantic Settings (не попадает в `repr()`)
- Rate limiting на чувствительные endpoints
- `with_for_update(skip_locked=True)` при выборе свободной VM (защита от race)
- Раздельные Pydantic-схемы `VirtualMachineResponse` (admin) и `VirtualMachinePublicResponse` (user, без `current_user_id`)
- Защита от выдачи бесполезных ключей (`ensure_free_vm_or_503` при register / refresh-key)

### Что НЕ реализовано

См. [Известные ограничения](../README.md#известные-ограничения) в корневом README.

---

## Celery

Запуск worker:

```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Параметры (`app/core/celery_app.py`):
- `task_acks_late=True` — задача подтверждается **после** успешного выполнения, не до. При падении worker'а задача перезапустится.
- `worker_prefetch_multiplier=1` — без предзагрузки, надёжнее для долгих задач
- `task_serializer="json"` — без pickle (безопаснее)

Email-задача `send_activation_key`:
- `autoretry_for=(Exception,)` — авторетрай любой ошибки
- `retry_backoff=True`, `retry_backoff_max=300` — exponential backoff до 5 минут
- `retry_jitter=True` — добавляет случайность чтобы избежать thundering-herd
- `max_retries=5`

---

## Rate limiting

См. [таблицу в корневом README](../README.md#rate-limiting). Storage — Redis, key — IP (учитывается `X-Forwarded-For` если есть).

---

## Тесты

```powershell
cd Backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -v
```

Используется **in-memory SQLite** + monkeypatch `send_activation_key.delay` (чтобы не пытаться реально слать email). См. `tests/conftest.py`.

**Что покрыто:**

| Файл | Что тестируется |
|---|---|
| `test_health.py` | `GET /` |
| `test_security.py` | bcrypt, JWT encode/decode, generate_activation_key |
| `test_auth.py` | register (success / duplicate / no_free_vms / inactive_vms), login, refresh, admin login |
| `test_profile.py` | get profile, refresh-key (success / no_free_vms / уже есть VM), не утекает activation_key в API |
| `test_activation.py` | success, invalid, expired, **no_free_vms — ключ остаётся валидным** |
| `test_ws.py` | все 4 WebSocket-статуса + отказ при невалидном токене |

**Не покрыто:**

- admin_vms endpoints (CRUD VM)
- user_vms endpoints (`/api/connect`, `/api/disconnect`, `/api/virtual-machines`)
- Concurrency-тесты для `SELECT FOR UPDATE` (SQLite их не поддерживает; нужен testcontainers с Postgres)
- Celery email task integration

---

## Troubleshooting

| Симптом | Причина | Решение |
|---|---|---|
| `ImportError: cannot import name 'EmailStr'` | Не установлен `email-validator` | `pip install email-validator` (он в requirements.txt) |
| `psycopg2.OperationalError: connection refused` | Postgres не запущен | `docker compose up -d postgres` или поправить `DATABASE_URL` |
| `kombu.exceptions.OperationalError` при старте Celery | Redis недоступен | `docker compose up -d redis` |
| `JWT decode error: Invalid algorithm` | Несовпадение `JWT_ALGORITHM` между токеном и текущим конфигом | Перевыдать токены (logout + login) |
| `503 All proxies are busy` при register | В пуле нет свободных VM | Админ должен добавить VM через `/admin` |
| `429 Too Many Requests` локально | Сработал rate-limiter | `RATE_LIMIT_ENABLED=false` в `.env` или `docker compose exec redis redis-cli FLUSHDB` |
| Email не приходит | Gmail требует **App Password**, не обычный пароль | Account → Security → 2-Step Verification → App passwords |
