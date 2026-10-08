---
name: actions-sheet-not-popover-in-clipped-tile
description: Действия карточки в контейнере с overflow: hidden — окном-списком на dialog, не выпадающим меню внутри карточки: обрежется
stack: [web-ui]
status: candidate
created: 2026-10-08
seen_in: [video-blade-2]
triggers:
  keywords: [overflow: hidden, меню в карточке, обрезается, details summary, popover, ⋯]
  commands: []
  errors: []
  paths: ["frontend/src/pages/*.vue", "static/css/*.css"]
---
# Действия карточки в контейнере с overflow: hidden — окном-списком на dialog, не выпадающим меню внутри карточки: обрежется

Контекст: меню «⋯» под картинкой задумывалось выпадающим внутри плитки, но плитка обрезает содержимое
(`overflow: hidden` ради скруглённых углов) — на коротком кадре меню обрезалось бы.

Урок:
- Действия карточки в контейнере с `overflow: hidden` показывай окном-списком на `<dialog>`: подпись карточки в
  заголовке, действия словами, опасное — красным; выпадающее меню внутри карточки не делай.
- Бонус: не нужен обработчик «клик мимо», на телефоне окно-список — привычный лист действий.
- Признак: `overflow: hidden` у карточки и меню с `position: absolute` внутри неё.
