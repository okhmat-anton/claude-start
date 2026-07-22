# Стек: Python FastAPI + Vue + PostgreSQL

Конвенции, проверенные в проектах пользователя.

## Backend
- Структура: `app/{api,core,db,models,schemas,services,tasks,utils}`.
- Сервисы — функциональный стиль (модуль с top-level `async def`), классы только
  для Pydantic-схем и SQLAlchemy-моделей; `from __future__ import annotations`,
  аннотации типов, `logging.getLogger(__name__)`.
- Настройки: pydantic-settings, singleton `settings = Settings()`,
  `env_file=".env"`, `extra="ignore"`, свойства-хелперы (`postgres_dsn`).
- Auth-зависимости: `get_current_user` (JWT), `get_current_admin`,
  `get_api_key_or_user` (JWT ИЛИ персональный X-API-Key — для внешних агентов).
- Ответ эндпоинта — явный dict; списки — `updated_at.desc()`.
- SQLAlchemy 2.0: `Mapped[]`, JSONB; новые таблицы — `create_all` на старте;
  новые колонки `create_all` НЕ добавляет — либо идемпотентные `ALTER TABLE`
  в startup, либо alembic.
- Тяжёлые операции (генерация контента) — Celery (+ RabbitMQ), realtime — Socket.IO.

## Frontend
- Vue 3 Composition API (`<script setup>`), Pinia, Vite; каталоги
  `api/ components/ composables/ pages/ layouts/ router/ stores/`.
- Персист форм — localStorage с префиксом проекта; loading-состояния у async;
  cleanup таймеров/подписок при unmount.

## Инфраструктура
- Docker Compose: БД с healthcheck, backend ждёт `service_healthy`; nginx
  reverse-proxy + certbot (SSL-конфиг генерируется из шаблона по домену).
- Порты — своя сотня на проект (например 4991 api / 4992 front / 4993 admin),
  чтобы dev-инстансы проектов не конфликтовали.
