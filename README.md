# Proxy Access Service

Сервис управления доступом пользователей к пулу прокси-серверов (виртуальных машин).

Пользователь регистрируется, получает на email одноразовый **ключ активации**, активирует его в десктоп-клиенте — и автоматически получает в распоряжение свободную VM из общего пула. Backend следит за состоянием подключения в реальном времени через WebSocket, админ управляет пулом VM через веб-панель.

---

## Содержание

- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Стек](#стек)
- [Быстрый старт](#быстрый-старт)
- [Структура репозитория](#структура-репозитория)
- [Переменные окружения](#переменные-окружения)
- [Web-страницы](#web-страницы)
- [Rate limiting](#rate-limiting)
- [Тесты](#тесты)
- [Полезные команды](#полезные-команды)
- [Подробная документация](#подробная-документация)

---

## Возможности

- **Регистрация и аутентификация** — JWT (access + refresh), bcrypt-хеши паролей, отдельные scope-ы для user/admin
- **Одноразовые активационные ключи** — выдаются на email, время жизни 7 дней, обновляются через `POST /profile/refresh-key`
- **Пул прокси-VM** — каждый активный пользователь привязан к одной свободной VM, привязка снимается командой `POST /api/disconnect`
- **Realtime-мониторинг** — WebSocket `/ws/connection-status` отдаёт статус подключения (`connected` / `disconnected` / `no_free_vms` / `error`)
- **Защита от выдачи бесполезных ключей** — backend не отправляет письмо с ключом, если в пуле нет свободных VM (отвечает `503`)
- **Админ-панель** — CRUD виртуальных машин, освобождение VM, просмотр занятости
- **Email-доставка через Celery** — отказоустойчивая (retries + exponential backoff)
- **Rate limiting** — глобальный (slowapi + Redis) и точечный на чувствительные ручки

---

## Архитектура

```
                          ┌────────────────────────┐
                          │      Frontend (Vue)    │
                          │  http://localhost:5173 │
                          └───────────┬────────────┘
                                      │ HTTPS/REST
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
   ┌────────▼──────────┐    ┌─────────▼──────────┐    ┌────────▼─────────┐
   │  Desktop (PyQt6)  │    │  Backend (FastAPI) │    │   Admin browser  │
   │  WebSocket +      │◄──►│  http://:8000      │◄──►│  /admin/*        │
   │  REST API client  │    └────┬────────┬──────┘    └──────────────────┘
   └───────────────────┘         │        │
                                 │        │
                       ┌─────────▼──┐  ┌──▼──────────────┐
                       │ PostgreSQL │  │     Redis       │
                       │  :5432     │  │  :6379          │
                       └────────────┘  │  ┌───────────┐  │
                                       │  │ slowapi   │  │
                                       │  │ broker    │  │
                                       │  └───────────┘  │
                                       └────────┬────────┘
                                                │
                                       ┌────────▼────────┐
                                       │  Celery worker  │
                                       │   (email)       │
                                       └────────┬────────┘
                                                │ SMTP
                                       ┌────────▼────────┐
                                       │   Gmail SMTP    │
                                       └─────────────────┘
```

**Поток активации**:

```
1. User → POST /auth/register (email + password)
2. Backend → проверяет, что в пуле есть свободные VM (иначе 503)
3. Backend → создаёт пользователя, генерирует activation_key
4. Backend → ставит Celery-задачу send_activation_key
5. Celery → отправляет email с ключом через SMTP
6. User → копирует ключ из письма в Desktop-клиент
7. Desktop → POST /api/activate-key { activation_key }
8. Backend → находит юзера, резервирует свободную VM (SELECT ... FOR UPDATE SKIP LOCKED)
9. Backend → возвращает access/refresh токены + connection info
10. Desktop → открывает WebSocket /ws/connection-status?token=...
11. Backend → каждые 3 сек шлёт текущий статус подключения
```

---

## Стек

| Слой | Технологии |
|---|---|
| **Backend** | Python 3.12, FastAPI 0.136, SQLAlchemy 2.0, Pydantic v2, python-jose (JWT), passlib (bcrypt) |
| **Async tasks** | Celery 5.6, Redis 7 |
| **Database** | PostgreSQL 16 |
| **Rate limiting** | slowapi + Redis backend |
| **Frontend** | Vue 3.5, Vuetify 3.11, Vue Router 4, Vite 5, MDI icons |
| **Desktop** | Python 3.11+, PyQt6, httpx, websocket-client |
| **DevOps** | Docker Compose, nginx (frontend reverse-proxy) |
| **Tests** | pytest, FastAPI TestClient, SQLAlchemy in-memory SQLite |

---

## Быстрый старт

### Запуск через Docker (рекомендуется)

```powershell
# 1. Создайте .env из примера и заполните секреты
Copy-Item .env.example .env

# 2. ОБЯЗАТЕЛЬНО замените плейсхолдеры в .env:
#    - JWT_SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(64))"
#    - ADMIN_PASSWORD: сильный пароль
#    - SMTP_USER / SMTP_PASSWORD: Gmail App Password
#      (Account → Security → 2-Step Verification → App passwords)

# 3. Запустите все сервисы
docker compose up -d --build

# 4. Откройте веб-интерфейс
start http://localhost:5173
```

После запуска доступно:

| URL | Назначение |
|---|---|
| `http://localhost:5173` | Web-интерфейс (Vue) |
| `http://localhost:8000` | Backend API |
| `http://localhost:8000/docs` | OpenAPI / Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

---

## Desktop-клиент

Десктоп распространяется как готовый `.exe` для Windows — Python и venv ставить не нужно.

**Скачать:** [Releases](../../releases/latest) → `ProxyAccess.exe`

Запуск: двойной клик. При первом запуске Windows может показать SmartScreen-предупреждение «Windows protected your PC» (норма для неподписанных приложений) — нажмите `More info` → `Run anyway`.

Адрес backend по умолчанию — `http://127.0.0.1:8000`. Изменить можно через переменную `PROXY_ACCESS_API_URL` или файл `.env` рядом с `.exe`:

```env
PROXY_ACCESS_API_URL=http://your-backend:8000
```

Для разработки (запуск из исходников) — см. [Desktop/README.md](Desktop/README.md).

---

## Структура репозитория

```
.
├── Backend/                       FastAPI + SQLAlchemy + Celery
│   ├── app/
│   │   ├── core/                  config, security (JWT, bcrypt), rate-limit, celery
│   │   ├── db/                    модели, сессия, инициализация, seed
│   │   ├── routers/               auth, profile, activation, ws, admin_vms, user_vms
│   │   ├── schemas/               Pydantic-схемы (Request/Response)
│   │   ├── services/              vm_pool (проверка пула), email_sender
│   │   ├── tasks/                 Celery-задачи (отправка email)
│   │   └── main.py                инициализация FastAPI + middleware
│   ├── tests/                     pytest (27+ тестов)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── Frontend/                      Vue 3 + Vuetify
│   ├── src/
│   │   ├── views/                 LoginView, RegisterView, ProfileView, AdminVmsView, AdminLoginView
│   │   ├── api.js                 клиент REST API + token storage
│   │   ├── adminApi.js            отдельный клиент для админ-эндпоинтов
│   │   ├── http.js                низкоуровневый fetch-обёртка
│   │   └── main.js                router + vuetify
│   ├── nginx.conf                 reverse-proxy + SPA fallback
│   ├── Dockerfile                 multi-stage build (node → nginx)
│   └── package.json
│
├── Desktop/                       PyQt6 клиент (бинарный .exe — в Releases)
│   ├── proxy_access/
│   │   ├── ui/                    main_window, sidebar, vm_card, connection_panel, activate_dialog
│   │   ├── api.py                 httpx-клиент к backend
│   │   ├── workers.py             QThread воркеры (API + WebSocket)
│   │   └── config.py              Session, dotenv
│   ├── run.ps1                    запуск из исходников (создаст venv)
│   └── requirements.txt
│
├── docker-compose.yml             5 сервисов: backend, frontend, postgres, redis, celery-worker
├── .env.example                   шаблон окружения
└── README.md                      ← вы здесь
```

---

## Переменные окружения

Все переменные читаются из корневого `.env`. Полный список — в [.env.example](.env.example).

### Обязательные

| Переменная | Назначение |
|---|---|
| `JWT_SECRET_KEY` | Подпись JWT-токенов. **Минимум 32 символа случайных байт.** Никогда не оставляйте дефолт. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Креды PostgreSQL |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | Креды Gmail (нужен **App Password**, не обычный пароль) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Учётка админа, создаётся автоматически при старте |

### Опциональные

| Переменная | Default | Назначение |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | TTL access-токена |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | TTL refresh-токена |
| `ACTIVATION_KEY_BYTES` | `32` | Длина ключа активации (в байтах до base64) |
| `RATE_LIMIT_ENABLED` | `true` | Можно отключить только для локальной отладки |
| `RATE_LIMIT_GLOBAL_PER_MINUTE` | `120` | Глобальный лимит на IP |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP-сервер |
| `SMTP_PORT` | `587` | STARTTLS (использовать 465 для SSL) |
| `VITE_API_URL` | `http://localhost:8000` | Адрес backend для фронта (передаётся при сборке) |

> **Безопасность.** Файл `.env` **не должен** попадать в git (он в `.gitignore`). Если случайно закоммитили — немедленно ротируйте все секреты.

---

## Web-страницы

| Маршрут | Доступ | Описание |
|---|---|---|
| `/register` | guest | Регистрация — после успеха ключ уходит на email |
| `/login` | guest | Вход по email + паролю |
| `/profile` | user | Личный кабинет: статус ключа, обновление ключа, смена пароля |
| `/admin/login` | guest | Вход админа (отдельный JWT-scope) |
| `/admin` | admin | Управление пулом VM: создание, обновление, удаление, освобождение |

Учётка администратора создаётся при первом старте backend из `ADMIN_EMAIL` / `ADMIN_PASSWORD`, если её ещё нет в БД (изменение пароля через ENV не применится — только через прямой SQL).

---

## Rate limiting

Backend использует [slowapi](https://github.com/laurentS/slowapi) с Redis-хранилищем.

| Endpoint | Лимит |
|---|---|
| `POST /auth/register` | 5/min на IP |
| `POST /auth/login` | 10/min |
| `POST /auth/refresh` | 30/min |
| `POST /auth/admin/login` | 10/min |
| `POST /api/activate-key` | 10/min |
| `POST /profile/refresh-key` | 5/min |
| `POST /profile/change-password` | 10/min |
| **Глобальный default** | 120/min на IP |

При превышении API отдаёт `429 Too Many Requests` с заголовком `Retry-After`.

Локально лимиты можно отключить:

```env
RATE_LIMIT_ENABLED=false
```

---

## Тесты

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -v
```

Покрыто:

- Auth: register (success/duplicate/no_free_vms/inactive_vms), login, refresh, admin login
- Activation: success, invalid key, expired, no_free_vms
- Profile: get, refresh-key (success / no_free_vms / уже есть VM)
- WebSocket: все 4 статуса (connected, disconnected, no_free_vms, error), отказ при невалидном токене
- Security, health

---

## Полезные команды

```powershell
# Логи backend
docker compose logs -f backend

# Логи Celery (доставка email)
docker compose logs -f celery-worker

# Подключиться в psql
docker compose exec postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB

# Очистить кеш limiter в Redis (если зафлудили локально)
docker compose exec redis redis-cli FLUSHDB

# Полный рестарт с пересборкой
docker compose down && docker compose up -d --build

# Остановить и УДАЛИТЬ данные PostgreSQL (опасно)
docker compose down -v
```

---

