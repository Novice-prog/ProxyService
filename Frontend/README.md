# Frontend — Proxy Access Web

Веб-интерфейс на Vue 3 + Vuetify 3. Через него пользователь регистрируется и управляет своим профилем, а админ — пулом VM.

---

## Содержание

- [Стек](#стек)
- [Структура](#структура)
- [Локальный запуск](#локальный-запуск)
- [Production-сборка](#production-сборка)
- [Переменные окружения](#переменные-окружения)
- [Маршруты](#маршруты)
- [Хранение токенов](#хранение-токенов)
- [Стилизация](#стилизация)
- [Иконки](#иконки)
- [Troubleshooting](#troubleshooting)

---

## Стек

| Компонент | Версия | Назначение |
|---|---|---|
| Vue | 3.5 | Composition API, SFC |
| Vuetify | 3.11 | Material-компоненты |
| Vue Router | 4.6 | роутинг, guards |
| Vite | 5.4 | dev-сервер + build |
| @mdi/font | 7.4 | иконки Material Design |
| nginx | 1.27-alpine | reverse-proxy + SPA fallback в production-образе |

---

## Структура

```
Frontend/
├── src/
│   ├── views/
│   │   ├── LoginView.vue          вход (email + пароль)
│   │   ├── RegisterView.vue       регистрация (после успеха — сообщение о письме)
│   │   ├── ProfileView.vue        статус ключа, refresh-key, смена пароля
│   │   ├── AdminLoginView.vue     отдельный логин для админа
│   │   └── AdminVmsView.vue       CRUD виртуальных машин
│   ├── api.js                     пользовательский REST-клиент + token store
│   ├── adminApi.js                клиент для админ-эндпоинтов (отдельный токен)
│   ├── http.js                    общий fetch-обёртка: разбор ошибок, Content-Type, Authorization
│   ├── main.js                    инициализация Vue, Router, Vuetify (явный список компонентов)
│   ├── App.vue                    корневой layout + <router-view>
│   └── styles.css                 глобальные CSS-переменные и стили карточек
├── index.html                     точка входа Vite
├── vite.config.js                 базовая конфигурация (порт, host)
├── nginx.conf                     reverse-proxy для production-образа
├── Dockerfile                     multi-stage: node:20 build → nginx:1.27 serve
└── package.json
```

---

## Локальный запуск

Нужны: Node.js 20+, npm.

```powershell
cd Frontend
npm install
npm run dev
```

Dev-сервер: `http://localhost:5173` (с hot reload).

Backend должен быть запущен отдельно (`docker compose up -d backend postgres redis celery-worker`) либо локально на 8000.

Адрес backend задаётся переменной `VITE_API_URL`:

```powershell
# временно
$env:VITE_API_URL = "http://localhost:8000"; npm run dev

# или создать Frontend/.env.local
# VITE_API_URL=http://localhost:8000
```

По умолчанию (если переменная не задана) — `http://localhost:8000` (см. `src/http.js`).

---

## Production-сборка

### Через Docker (как в docker-compose)

```powershell
docker compose up -d --build frontend
# доступно на http://localhost:5173
```

В этом случае `VITE_API_URL` передаётся как `--build-arg` в Dockerfile (см. `docker-compose.yml`).

### Локально

```powershell
cd Frontend
npm run build      # → dist/
npm run preview    # быстрый локальный сервер для проверки билда
```

Содержимое `dist/` можно деплоить любым статик-хостингом (nginx, S3+CloudFront, Vercel, Cloudflare Pages).

---

## Переменные окружения

Vite читает переменные с префиксом `VITE_*` во время **сборки**, не runtime. Если меняешь — пересобирай.

| Переменная | Где используется | Default |
|---|---|---|
| `VITE_API_URL` | `src/http.js:1` — базовый URL для всех запросов | `http://localhost:8000` |

Файлы (по приоритету Vite):
- `.env.production.local`
- `.env.production`
- `.env.local`
- `.env`

---

## Маршруты

Описаны в `src/main.js:41-64`. Guard'ы:
- `meta.requiresAuth: true` → редирект на `/login`, если нет токена
- `meta.guestOnly: true` → редирект на `/profile`, если уже залогинен
- Админские маршруты используют отдельный guard на `isAdminAuthenticated`

| Path | View | Guard |
|---|---|---|
| `/` | redirect | → `/login` |
| `/register` | `RegisterView` | guestOnly |
| `/login` | `LoginView` | guestOnly |
| `/profile` | `ProfileView` | requiresAuth |
| `/admin/login` | `AdminLoginView` | если уже admin → `/admin` |
| `/admin` | `AdminVmsView` | если не admin → `/admin/login` |

---

## Хранение токенов

Текущая реализация (`src/api.js:4-5`):

```js
const accessToken  = ref(localStorage.getItem('access_token'))
const refreshToken = ref(localStorage.getItem('refresh_token'))
```

Токены лежат в `localStorage` и зеркалятся в Vue-ref для реактивности `isAuthenticated`.

При получении `401`:
1. `authRequest()` ловит ошибку
2. Зовёт `refreshAccessToken()` (одна параллельная попытка благодаря `refreshRequestPromise`)
3. Повторяет исходный запрос с новым access-токеном
4. Если refresh тоже отдал `401` → токены чистятся, редирект на `/login`

> **Известное ограничение.** Хранение access/refresh в `localStorage` уязвимо к XSS. В production-проекте refresh-токен должен лежать в `HttpOnly Secure SameSite=Strict cookie`, а access — только в JS-памяти. См. P1.7 в аудите.

---

## Стилизация

- **Vuetify тема** (`src/main.js:109-125`) — единственная светлая тема `serviceTheme`, primary `#2563eb`.
- **Глобальные стили** (`src/styles.css`) — переменные `--*`, утилитарные классы (`page-inner`, `dashboard-card`, `glass-card` и т.д.).
- **Component-scoped стили** — отсутствуют, у компонентов чистый HTML с глобальными классами. Это упрощает рефакторинг, но имеет риск конфликтов имён — будь внимателен при добавлении новых классов.

---

## Иконки

Используется **Material Design Icons** (`@mdi/font@7.4.47`). Каноничный каталог: [pictogrammers.com/library/mdi](https://pictogrammers.com/library/mdi/).

**Важно:** при использовании `prepend-inner-icon="mdi-XXX"` Vuetify **не валидирует** имя иконки. Если глифа нет в шрифте, рендерится либо пусто, либо двумя соседними глифами. Всегда проверяй точное имя на каталоге MDI.

Примеры безопасных иконок (использованы в проекте):
- `mdi-lock-outline`, `mdi-lock-plus-outline`, `mdi-lock-check-outline`
- `mdi-email-outline`, `mdi-email-check-outline`
- `mdi-key-variant`, `mdi-key-outline`
- `mdi-account-shield-outline`, `mdi-view-dashboard-outline`

---

## Troubleshooting

| Симптом | Причина | Решение |
|---|---|---|
| `Failed to fetch` в DevTools | Backend не запущен или неверный `VITE_API_URL` | Запустить backend; пересобрать с правильным URL |
| CORS error в консоли | Origin не разрешён в backend | См. `Backend/app/main.py:25-37` — добавить origin в `allow_origins` |
| Иконка не отображается / две иконки рядом | Несуществующее имя `mdi-*` | Проверить на pictogrammers.com |
| `Cannot read property of undefined` после логина | Старый `localStorage` остался от прежней схемы | DevTools → Application → Local Storage → очистить |
| `npm run dev` падает с `ENOENT package.json` | Запустили из корня вместо `Frontend/` | `cd Frontend && npm run dev` |
| После `docker compose build frontend` фронт всё ещё со старым API URL | Build-time переменная не передалась | `docker compose build --no-cache --build-arg VITE_API_URL=... frontend` |
| 404 на любом URL кроме корня (после деплоя) | Не настроен SPA fallback на nginx/хостинге | См. `Frontend/nginx.conf` — `try_files $uri $uri/ /index.html;` |

---

## Скрипты (`package.json`)

```bash
npm run dev      # vite dev-server на 0.0.0.0:5173
npm run build    # production-билд в dist/
npm run preview  # быстрый просмотр готового build'а
```
