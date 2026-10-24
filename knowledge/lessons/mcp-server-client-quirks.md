---
name: mcp-server-client-quirks
description: Удалённый MCP-сервер под Claude Code / Cursor / Codex: 401 без OAuth-метаданных, GET → 405, scope папки, deeplink Cursor, проверка Inspector и claude -p
stack: [llm]
status: candidate
created: 2026-10-23
seen_in: [video-blade-2]
triggers:
  keywords: [MCP, Model Context Protocol, Streamable HTTP, claude mcp add, Cursor, Codex, Bearer, WWW-Authenticate, Inspector, tools/list, deeplink]
  commands: ['claude mcp (add|list)', 'codex mcp add', 'modelcontextprotocol/inspector']
  errors: ['Failed to connect', 'Method Not Allowed']
  paths: []
---
# Удалённый MCP-сервер под Claude Code / Cursor / Codex: что проверить и как не споткнуться

Контекст: сервер MCP на Streamable HTTP с ключом в заголовке Bearer для трёх клиентов; проверка настоящими клиентами
на стенде вместо веры в спецификацию.

Урок:
- 401 отдавай без `WWW-Authenticate` с OAuth-метаданными — иначе клиент может уйти в OAuth вместо заданного заголовка.
- В режиме без состояния на GET отвечай 405: пустой SSE-поток только держит соединения и рвётся прокси по таймауту;
  человеку из браузера (Accept: text/html) — редирект на страницу подключения.
- `claude mcp add` без `-s user` регистрирует сервер на папку, а уже открытая сессия новый сервер не видит — в инструкции
  скажи про новую сессию и про папку.
- В deeplink установки Cursor `config` — сама запись сервера (`{"url", "headers"}`), не обёртка `mcpServers`.
- Codex берёт ключ из переменной окружения (`--bearer-token-env-var`) при каждом старте — инструкция обязана это сказать.
- Совместимость подтверждай эталонным Inspector (`--cli … --method tools/list`) и живым прогоном
  `claude -p … --mcp-config … --strict-mcp-config`; ход вызова — в транскрипте сессии.
