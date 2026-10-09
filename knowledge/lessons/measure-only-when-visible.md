---
name: measure-only-when-visible
description: Размер элемента (авторост поля) мерить только видимым (offsetParent) и заново при показе вкладки после nextTick — скрытое поле даёт scrollHeight 0
stack: [web-ui]
status: candidate
created: 2026-10-09
seen_in: [video-blade-2]
triggers:
  keywords: [scrollHeight, авторост, textarea, v-show, скрытая вкладка, offsetParent, display none]
  commands: []
  errors: []
  paths: []
---
# Размер элемента мерить только видимым, при показе вкладки — заново

Контекст: поле «растёт под текст» мерили при монтировании, пока его вкладка была скрыта (`display: none`):
scrollHeight 0 → высота 2 px, текст срезан на компьютере и телефоне; тесты этого не видят.

Урок:
- перед измерением проверяй, что элемент виден (`offsetParent !== null`), иначе не трогай его размеры;
- при показе вкладки, окна или раскрытии блока мерь заново после `nextTick` (DOM уже перерисован);
- признак заранее: авторост, выравнивание по высоте или прокрутка к элементу внутри `v-show`, `<details>`,
  `<dialog>` или другой вкладки.
