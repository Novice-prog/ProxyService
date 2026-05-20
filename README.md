# Proxy Access Service

## Запуск через Docker

1. Создайте `.env` из примера:

```powershell
Copy-Item .env.example .env
```

2. Заполните в `.env` секреты и SMTP-настройки Gmail:

```env
SMTP_USER=your.email@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM_EMAIL=your.email@gmail.com
```

Для Gmail нужен пароль приложения Google, а не обычный пароль от почты.

3. Запустите проект:

```powershell
docker compose up -d --build
```

Backend будет доступен на:

```text
http://localhost:8000
```

Frontend будет доступен на:

```text
http://localhost:5173
```

Swagger:

```text
http://localhost:8000/docs
```

## Сервисы

- `backend` - FastAPI API.
- `frontend` - Vue 3 + Vuetify веб-интерфейс.
- `postgres` - база данных PostgreSQL.
- `redis` - брокер и backend результатов Celery.
- `celery-worker` - отправка email с ключами активации.

## Локальная разработка frontend

Если backend уже запущен через Docker, frontend можно запускать отдельно:

```powershell
cd Frontend
npm install
npm run dev
```

Откройте:

```text
http://localhost:5173
```

Frontend отправляет запросы в backend по адресу `VITE_API_URL`. По умолчанию используется:

```text
http://localhost:8000
```

## Основные страницы

- `/register` - регистрация пользователя.
- `/login` - вход.
- `/profile` - личный кабинет, обновление ключа и смена пароля.
- `/admin/login` - вход администратора.
- `/admin` - админ-панель виртуальных машин.

Учётная запись администратора создаётся при старте backend из переменных `ADMIN_EMAIL` и `ADMIN_PASSWORD` в `.env` (только если такого email ещё нет в базе).


## Полезные команды

Посмотреть логи backend:

```powershell
docker compose logs -f backend
```

Посмотреть логи Celery:

```powershell
docker compose logs -f celery-worker
```

Остановить проект:

```powershell
docker compose down
```

Остановить проект и удалить данные PostgreSQL:

```powershell
docker compose down -v
```
