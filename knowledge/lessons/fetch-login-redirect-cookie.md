---
name: fetch-login-redirect-cookie
description: Вход формой через fetch — 303 с cookie ловить с redirect:'manual', иначе cookie теряется, а вход выглядит успешным
stack: [web-ui]
status: candidate
created: 2026-09-27
seen_in: [video-blade-2]
triggers:
  keywords: [вход формой, Set-Cookie, 303, redirect manual, headless, cookie теря, экран входа, look.js, не залогин]
  commands: ['look\.js (shot|run|open)', 'curl .*-d .*(login|signin)']
  errors: []
  paths: ['**/look.js', '**/auth.json']
---
# Вход формой через fetch: cookie живёт в 303, а fetch его проходит и теряет

Контекст: инструмент кадров для ревью логинился POST-ом JSON и брал cookie из ответа. Приложение со входом
HTML-формой отвечает 303 и кладёт cookie в редирект; `fetch` прошёл редирект сам, cookie промежуточного ответа
потерял и ошибки не дал — «вход прошёл», а на кадрах экран входа.

Урок:
- Вход формой через `fetch` — `redirect: "manual"` и cookie из самого 303; успех — статус < 400, а не `r.ok`
  (для 303 он ложный).
- Признак: логин «успешен», но первый же кадр или запрос показывает страницу входа — ищи потерянный
  редирект, а не пароль.
- В `auth.json` инструмента держи оба вида входа (`json` для API, `form` для HTML-формы), чтобы не править
  код под каждый проект.
