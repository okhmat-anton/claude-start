---
name: nginx-stale-upstream-after-recreate
description: nginx в docker compose разрешает имя сервиса в proxy_pass один раз при старте; пересоздал контейнер приложения — 502, лечится nginx -s reload или resolver 127.0.0.11 с переменной
index: nginx в compose держит старый адрес пересозданного контейнера — 502 при живом приложении; nginx -s reload или resolver
stack: [docker]
status: candidate
created: 2026-10-05
seen_in: [planning]
triggers:
  keywords: [nginx, 502, docker compose up, proxy_pass, make update, deploy]
  commands: []
  errors: [connect() failed (111: Connection refused) while connecting to upstream]
  paths: []
---
# После пересоздания контейнера nginx шлёт запросы на старый адрес — 502 при живом приложении

Контекст: выкладка через `docker compose up -d --build` пересоздала контейнер приложения (и соседний сервис),
приложение получило новый внутренний адрес, а nginx, работающий месяцами без перезапуска, слал запросы на
старый — сайт целиком отдавал 502. Скрипт выкладки при этом напечатал верный коммит, в журнале приложения было
«listening»: всё выглядело успешным. Раньше проскакивало, потому что адрес случайно совпадал.

Урок:
- После выкладки проверяй публичный адрес (`curl -w '%{http_code}'`), а не только журнал и коммит.
- 502 + в журнале nginx `connect() failed (111: Connection refused) while connecting to upstream` с адресом,
  которого нет у контейнера (`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'`),
  при этом приложение отвечает изнутри (`docker exec <app> wget -qO- 127.0.0.1:<порт>`) — это не откат,
  а `docker exec <nginx> nginx -s reload`.
- Причина: `proxy_pass http://<сервис>:<порт>` без `resolver` — имя разрешается один раз при старте nginx.
  Постоянно: `resolver 127.0.0.11 valid=10s;` + адрес через переменную (`set $up http://app:5173; proxy_pass $up;`)
  либо `nginx -s reload` последним шагом скрипта выкладки.
