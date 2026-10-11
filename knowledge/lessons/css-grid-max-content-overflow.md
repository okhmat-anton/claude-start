---
name: css-grid-max-content-overflow
description: Сетка с колонками max-content и текстом шире контейнера — страница едет вбок; колонки auto-fit/minmax или flex с переносом
stack: [web-ui]
status: candidate
created: 2026-10-11
seen_in: [video-blade-2]
triggers:
  keywords: [max-content, grid-template-columns, обрезан, прокрутка вбок, строка значков]
  commands: []
  errors: []
  paths: ["static/css/*.css", "landing/*.html", "frontend/src/**/*.vue"]
---
# Сетка с колонками max-content и текстом шире контейнера — страница едет вбок; колонки auto-fit/minmax или flex с переносом

Контекст: полоса из семи коротких гарантий со значками сверстана сеткой `repeat(4, max-content)`; при фразах длиннее
ожидаемого сетка стала шире контейнера, страница получила горизонтальную прокрутку, ревью поставило блокер.

Урок:
- колонки с текстом — `repeat(auto-fit, minmax(<ширина>, 1fr))` или flex с переносом; `max-content` — только для
  элементов фиксированного размера;
- после правки сетки снимай кадр на 1440 и на 1280: на ноутбуке переполнение видно раньше;
- признак: `max-content` в `grid-template-columns` рядом с фразами, которые редактирует человек.
