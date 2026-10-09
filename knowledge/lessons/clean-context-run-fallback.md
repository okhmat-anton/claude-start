---
name: clean-context-run-fallback
description: Чистый прогон claude -p: --bare не залогинен по подписке — пустая папка + --setting-sources "" --tools ""; --json-schema даёт structured_output
stack: [llm]
status: candidate
created: 2026-10-09
seen_in: [video-blade-2]
triggers:
  keywords: [чистый контекст, --bare, claude -p, setting-sources, json-schema, судья]
  commands: ['claude -p', '--bare', '--json-schema']
  errors: ['Not logged in']
  paths: []
---
# Чистый прогон claude -p без --bare

Контекст: прогон промта «как у чужого агента» — пустая папка, без памяти и файлов проекта. `claude -p --bare`
на машине с подпиской отвечает «Not logged in» (bare отключает чтение связки ключей); бинарник в PATH
оболочки отсутствует — лежит в расширении редактора.

Урок:
- Чистый прогон: пустая временная папка + `--setting-sources "" --tools "" --no-session-persistence
  --output-format json`; проверь первый ответ полем `is_error`, а не кодом выхода.
- Судья — тот же запуск с `--json-schema`: структурированный ответ приходит в `structured_output`.
- Исполнитель и судья — разные запуски; не больше трёх параллельно; исполнитель 40–130 с на текст, судья
  секунды.
- Признак: `terminal_reason: api_error` с нулём токенов — не сеть, а авторизация.
