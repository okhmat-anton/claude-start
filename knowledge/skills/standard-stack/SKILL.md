---
name: standard-stack
description: Единый стандарт стека, стиля кода и деплоймента для всех проектов пользователя. Применяй при старте нового проекта (/start) и при любых решениях «как тут принято»: команды, именование, git, секреты, деплой.
---

# Стандарт стека и деплоймента

## Стек по умолчанию
Python 3.12 + FastAPI (backend), Vue 3 / vanilla JS (frontend), PostgreSQL (данные),
Docker Compose + nginx reverse-proxy (+ certbot SSL), pip (requirements.txt,
версии запинены `==`) + npm. Топология: app-сервисы за nginx, `restart: always`,
healthcheck у БД, backend `depends_on: condition: service_healthy`.

## Команды — всегда через Makefile (единый интерфейс)
- `make run` — docker compose up -d --build
- `make run-dev` — базы в docker + uvicorn --reload + vite dev
- `make stop` / `make logs` / `make status`
- `make test` — pytest (backend); фронтовые тесты добавляются как npm run test
- `make lint` — ruff check + ruff format --check (+ eslint при фронте)
- `make format` — ruff format (+ prettier)
- `make build` — docker compose build
- `make update` — деплой на сервере: git pull --rebase --autostash + build + up -d

Вопросы «какая команда тестов/линта/сборки/запуска» в новых проектах НЕ задаются —
это стандарт; интервью /start предзаполняется этими значениями.

## Именование
Python — snake_case (PEP8), приватные хелперы `_prefix`, файлы snake_case.py;
JS — camelCase, простые модули kebab-case.js; классы и Vue-компоненты — PascalCase
(PascalCase.vue); константы — UPPER_CASE. camelCase в Python не применяется.

## Git
Conventional Commits: `feat|fix|refactor|docs(scope): описание`. Одна ветка main
(trunk-based), без feature-веток. Деплой: локально commit + push → на сервере
`ssh <хост> 'cd <проект> && make update'` → health-check (curl API + первая страница).

## Секреты и env
`.env` (gitignored) + `.env.example` (в git). Генерация секретов:
`openssl rand -hex 32`. В коде — pydantic-settings singleton, поля UPPER_CASE.
Ключи внешних API — из настроек/БД (переопределяемо через админку), никогда
в коде и никогда в чат/логи. `*.pem`, `*.key` — в .gitignore.

## Качество
Линт ruff — с первого python-файла. Каждый найденный баг → регрессионный тест
(pytest появляется вместе с первым багом, если не раньше). Правила поведения
агента: компактный CLAUDE.md + .claude/rules/ с glob-привязкой к путям.

<!-- from business-planner /start, 2026-07-22 -->
