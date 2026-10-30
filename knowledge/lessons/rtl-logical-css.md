---
name: rtl-logical-css
description: Справа налево: отступы и позиции — inset-inline, margin-inline, text-align: start; стрелки «назад/вперёд» зеркалятся
stack: [web, css]
status: candidate
created: 2026-10-30
seen_in: [gym-bro-3]
triggers:
  keywords: [rtl, арабский, margin-inline, inset-inline, text-align start, стрелки]
  commands: []
  errors: []
  paths: []
---
# Справа налево: логические свойства и зеркальные стрелки

Контекст: арабский интерфейс зеркалился сам (`dir=rtl`), но «глазок» пароля стоял там, где начинается текст, стрелки
недели смотрели внутрь, логотип прилипал к плашке — всё из-за `left/right`, `margin-right: auto`, `text-align: left` и
стрелок-иконок без отражения.

Урок:
- Отступы и позиции — логическими свойствами: `inset-inline-start/end`, `margin-inline-*`, `padding-inline-*`,
  `text-align: start`; в физических `left/right` остаётся только симметричное.
- Иконки «назад/вперёд/открыть» отражаются под `[dir=rtl]` (`transform: scaleX(-1)`), «вверх/вниз» — нет.
- Проверка — кадры экранов на арабском (вход, список, карточка, шапка, переключатели).
