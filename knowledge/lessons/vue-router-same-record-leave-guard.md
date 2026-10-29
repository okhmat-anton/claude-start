---
name: vue-router-same-record-leave-guard
description: Экраны на одном маршруте `/:screen/:variant`: переход между ними для vue-router — update, `onBeforeRouteLeave` не срабатывает, нужен и `onBeforeRouteUpdate`
stack: [vue]
status: candidate
created: 2026-10-29
seen_in: [gym-bro-3]
triggers:
  keywords: [onBeforeRouteLeave, onBeforeRouteUpdate, один маршрут, :screen, не сработал, guard, несохранён, route record, beforeRouteLeave]
  commands: []
  errors: []
  paths: ['src/router.js', 'src/screens/**/*.vue']
---
# Один маршрут на все экраны: уход с экрана для vue-router — update, не leave

Контекст: страница правки с вопросом «Save / Discard» на уход зарегистрировала `onBeforeRouteLeave`; тап по вкладке Today уводил без вопроса. Все экраны макета живут на одной записи `/mock/:screen/:variant`, и смена screen — это `onBeforeRouteUpdate`; «leave» срабатывает только при смене записи.

Урок:
- Guard на уход со страницы, если экраны делят одну запись маршрута: регистрируй одну функцию и в `onBeforeRouteLeave`, и в `onBeforeRouteUpdate`.
- Guard регистрирует каждый экземпляр компонента маршрута — ограничь его своим экраном (`route.params.screen === …` при setup), иначе переход на страницу правки с Today спросит «сохранить?» у Today.
- Проверка: уйти по вкладке, по ссылке и по адресу, на кадре печатать итоговый URL — вопрос должен появиться во всех трёх случаях.
- Признак: `routes` с одной записью и параметром-экраном, guard «иногда не срабатывает».
