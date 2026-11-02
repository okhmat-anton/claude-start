---
name: embedded-postgres-when-docker-stuck
description: Docker завис (docker info молчит 15 с) — pgserver в отдельном venv, роль и базы как в compose, DATABASE_URL через сокет: тесты и стенд через 20 с
stack: [python, postgres, docker]
status: candidate
created: 2026-11-01
seen_in: [gym-bro-3]
triggers:
  keywords: [docker завис, docker info, timeout, pgserver, postgres, тесты не идут, стенд, compose up]
  commands: ['docker (info|ps|compose)']
  errors: ['docker.*(timeout|unresponsive|не отвечает)']
  paths: ['docker-compose*.yml']
---
# Docker завис — тесты на встроенном Postgres, а не ожидание

Контекст: Docker Desktop перестал отвечать (`docker info` и `compose up -d db` висели минутами); перезапуск через quit
и open не помог, принудительное убийство процессов харнесс запретил. Тесты и стенд ждали базу.

Урок:
- `docker info` не ответил за 15 секунд — не жди и не убивай: отдельный venv, `pip install pgserver`, сервер на
  unix-сокете, роль и базы как в compose, `DATABASE_URL=postgresql+asyncpg://user:pass@/db?host=<сокет>` — тесты и
  стенд через 20 секунд.
- Запускай скрипт с сервером фоном и держи процесс живым: pgserver гасит базу при выходе из Python.
- Владельцу скажи перезапустить Docker руками; признак — процессы com.docker.backend живы, а CLI молчит.
