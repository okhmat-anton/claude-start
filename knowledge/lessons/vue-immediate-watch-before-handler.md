---
name: vue-immediate-watch-before-handler
description: watch(…, {immediate}) в <script setup> выше const-обработчика — ReferenceError при монтировании: обработчики объявляй выше немедленных наблюдателей
stack: [vue]
status: candidate
created: 2026-10-21
seen_in: [video-blade-2]
triggers:
  keywords: [immediate, watch, before initialization, script setup, TDZ, автосохранение]
  commands: []
  errors: ['Cannot access .* before initialization']
  paths: []
---

# Немедленный watch выше объявления обработчика — падение при монтировании

Контекст: в `<script setup>` карточка с автосохранением объявила `watch(source, handler, { immediate: true })` выше
`const save = …`, который handler вызывает; компонент падал при монтировании с ReferenceError, серверные тесты
страниц зелёные — нашлось только по кадрам стенда.

Урок:
- Обработчики, таймеры и вспомогательные функции объявляй выше `watch(…, { immediate: true })`, `watchEffect` и
  `onMounted`, либо пиши их `function name() {}` — объявление функции поднимается, а `const` ниже точки вызова живёт
  во временной мёртвой зоне.
- Признак заранее: `immediate: true` или `watchEffect` в верхней трети файла, а `const`-стрелки — ниже.
- «Cannot access '…' before initialization» в консоли браузера при открытии страницы — это она; ловится только
  кадром или консолью стенда, не тестами API.
