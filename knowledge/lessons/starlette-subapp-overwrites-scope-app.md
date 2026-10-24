---
name: starlette-subapp-overwrites-scope-app
description: Вложенное Starlette-приложение пишет в scope["app"] себя: Request, который ты держишь, теряет state родителя — копируй scope до передачи
stack: [fastapi]
status: candidate
created: 2026-10-23
seen_in: [video-blade-2]
triggers:
  keywords: [scope app, request.app, state, вложенное приложение, sub-app, mount, каталог из state]
  commands: []
  errors: ["'State' object has no attribute", "KeyError: 'app'"]
  paths: ['app/routers/*.py', 'app/main.py']
---
# Вложенное Starlette-приложение пишет в scope["app"] себя — Request, который ты держишь, теряет state родителя

Контекст: обёртка перед вложенным ASGI-приложением (сервер MCP из SDK) создавала Request из scope и клала его
в contextvar для обработчиков. Вложенное приложение при вызове записало в тот же scope["app"] себя; `request.app.state`
стал пустым — обработчики не нашли каталог моделей родительского приложения.

Урок:
- Request, который переживёт вызов вложенного ASGI-приложения, строй на копии scope: `Request(dict(scope), receive)` —
  вложенное приложение изменит свой словарь, а твой сохранит app родителя.
- Признак: `request.app.state.<поле>` падает только внутри инструментов вложенного приложения, а в обычных маршрутах
  работает.
