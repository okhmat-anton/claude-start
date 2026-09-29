---
name: headless-chrome-accept-language
description: Язык headless-браузера — CDP-заголовком Accept-Language, не флагом --lang (macOS его игнорирует); один источник языка, проверка эхо-сервером
stack: [web-ui]
status: candidate
created: 2026-09-29
seen_in: [video-blade-2]
triggers:
  keywords: [--lang, Accept-Language, headless Chrome, язык интерфейса, кадры не на том языке, setUserAgentOverride]
  commands: ['look\.js (run|shot)', '--lang=']
  errors: []
  paths: []
---
# Язык headless-браузера — заголовком через CDP, не флагом запуска

Контекст: инструмент кадров запускал Chrome с `--lang=ru-RU`, а сервер выбирал язык по Accept-Language. На macOS
Chrome флаг игнорирует и шлёт системный язык, а в подмене User-Agent был зашит `acceptLanguage: "ru-RU"` —
ревью английского интерфейса шло по-русски.

Урок:
- Язык браузера в headless-прогоне задавай через CDP `Network.setUserAgentOverride.acceptLanguage`, не флагом `--lang`.
- В инструменте один источник языка (параметр `--lang`) и для флага, и для заголовка — иначе они расходятся молча.
- Кадры не на том языке — сначала эхо-сервер (маленький http-сервер, печатающий заголовки), чтобы увидеть, какой
  Accept-Language реально пришёл, а не править приложение.
