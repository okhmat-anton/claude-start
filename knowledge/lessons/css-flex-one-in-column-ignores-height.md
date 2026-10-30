---
name: css-flex-one-in-column-ignores-height
description: flex: 1 в flex-колонке забирает у элемента фиксированную высоту (кнопка 64 px рисуется 24 px): у такого элемента — flex: none
stack: [web-ui, vue]
status: candidate
created: 2026-10-30
seen_in: [gym-bro-3]
triggers:
  keywords: [flex: 1, flex-direction: column, высота, кнопка, flex: none, футер]
  commands: []
  errors: []
  paths: ['*.vue', '*.css']
---
# Элемент фиксированной высоты в flex-колонке — flex: none

Контекст: главная кнопка экрана с height: 64px рисовалась 24 px: в колонке с авто-высотой flex: 1 (основа 0 %) берёт высоту по содержимому, а height игнорируется; висело с первого коммита.

Урок:
- У элемента фиксированной высоты в flex-колонке — `flex: none`; `flex: 1` — только по оси, где есть свободное место.
- Проверка: кадр экрана с главной кнопкой после каждой правки подвала или футера.
- Признак: в стилях `flex: 1` у кнопки внутри `flex-direction: column`.
