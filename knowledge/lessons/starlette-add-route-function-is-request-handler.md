---
name: starlette-add-route-function-is-request-handler
description: add_route с функцией делает из неё обработчик Request→Response; чистому ASGI-приложению нужен вызываемый объект; Mount("/x") редиректит /x на /x/
stack: [fastapi]
status: candidate
created: 2026-10-23
seen_in: [video-blade-2]
triggers:
  keywords: [add_route, ASGI, receive, send, Mount, redirect_slashes, endpoint, обёртка ASGI]
  commands: []
  errors: ["missing 2 required positional arguments: 'receive' and 'send'"]
  paths: ['app/routers/*.py']
---
# add_route с функцией делает из неё обработчик Request→Response; чистому ASGI-приложению нужен вызываемый объект

Контекст: калитка ключа перед вложенным ASGI-приложением была функцией `(scope, receive, send)`, подключённой через
`add_route`; Starlette обернул её как обработчик Request и вызвал с одним аргументом. Mount("/mcp") не подошёл:
он редиректит `/mcp` на `/mcp/`, а клиенты протокола редирект POST не проходят.

Урок:
- Чистое ASGI-приложение в `add_route` — вызываемый объект (класс с `__call__`): функцию Starlette всегда считает
  обработчиком Request.
- Mount для адреса без завершающего слеша не подходит: `Mount("/x")` отвечает на `/x` редиректом на `/x/`.
- Признак: `TypeError: missing 2 required positional arguments: 'receive' and 'send'` из middleware-стека.
