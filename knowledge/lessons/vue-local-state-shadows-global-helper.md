---
name: vue-local-state-shadows-global-helper
description: Локальное состояние <script setup> с именем глобального помощника шаблона (duration, tokens) перекрывает его молча — страница пустая при зелёных тестах
stack: [vue, web-ui]
status: candidate
created: 2026-10-09
seen_in: [video-blade-2]
triggers:
  keywords: [глобальный форматтер, script setup, globalProperties, пустая страница, перекрыл, duration is not a function]
  commands: []
  errors: ['is not a function', 'is not iterable']
  paths: ['frontend/src/pages/*.vue', 'src/pages/*.vue']
---
# Локальное состояние <script setup> с именем глобального помощника шаблона (duration, tokens) перекрывает его молча — страница пустая при зелёных тестах

Контекст: на странице с формой заказа локальное состояние `duration` (длительность клипа) закрыло глобальный форматтер
`duration()` шаблонов (`app.config.globalProperties`) — страница отрисовывалась пустой, а серверные тесты и тесты по
разметке были зелёными.

Урок:
- Имена глобальных помощников шаблона (форматтеры, переводчик) — запретный список для локального состояния; локальное
  называй по смыслу поля (`seconds`, `clipLength`), список имён держи в правилах проекта.
- Пустая страница при зелёных тестах — первым делом ошибки консоли браузера через инструмент кадров, а не чтение кода.
- Признак: страница падает только в браузере, в консоли `… is not a function` / `is not iterable` на имени помощника.
