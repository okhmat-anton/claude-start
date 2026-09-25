---
name: browser-check-raw-cdp
description: Живой прогон UI без Playwright — стенд с базой в памяти и сырой DevTools-протокол через websockets; DOM-узел из evaluate — {}, условия в !!()
stack: [web-ui]
status: candidate
created: 2026-09-24
seen_in: [video-blade-2]
triggers:
  keywords: [headless, cdp, devtools, живой прогон, скриншот, websockets, Runtime.evaluate, стенд]
  commands: []
  errors: []
  paths: []
---
# Живой прогон UI через сырой CDP и стенд с базой в памяти

Контекст: нужно было проверить редактор с черновиком, уходом со страницы и конфликтом сохранений, а Docker и
Playwright на машине не было. Помог стенд с базой в памяти и прямой протокол DevTools через `websockets`.

Урок:
- Стенд: отдельный процесс на свободном порту, подмена клиента базы на in-memory (как в фикстурах тестов),
  ключ админки генерируется и пишется в файл рядом, не в argv; реальные базы и внешние сервисы не трогаются.
- Chrome `--headless=new --remote-debugging-port=N --user-data-dir=<временная>`; команды — `Runtime.evaluate`
  с `awaitPromise` и `returnByValue`.
- DOM-узел из `evaluate` приходит как `{}`, а в Python это ложь: условие ожидания оборачивай в `!!(…)`.
- Переход ждать меткой: `window.__old = true` до навигации, готово — когда метки нет и `readyState` complete.
- Сценарии без ручных действий: `window.confirm = () => true`; истёкшая сессия — `Network.deleteCookies`;
  упавший CDN — `Network.setBlockedURLs`; ⌘S — `Input.dispatchKeyEvent` с `modifiers=4` и `code=KeyS`.
- Сценарий рассчитан на чистую базу: перед повтором перезапусти стенд.
