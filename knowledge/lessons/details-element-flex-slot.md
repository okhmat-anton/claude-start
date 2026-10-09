---
name: details-element-flex-slot
description: Содержимое <details> — отдельный слот: display:flex на details ставит summary и тело рядом; раскладывай text-align/flex-basis на самом details
stack: [web-ui]
status: candidate
created: 2026-10-09
seen_in: [video-blade-2]
triggers:
  keywords: [details, summary, flex, слот, раскрыв]
  commands: []
  errors: []
  paths: ['static/css/*.css', 'templates/**/*.html']
---
# Содержимое details — отдельный слот

Контекст: раскрывающаяся форма на `<details>`: `display:flex` на самом элементе поставил тело формы рядом с
кнопкой-summary, а не под ней — содержимое details рендерится в отдельном слоте, flex-basis ему не задать.

Урок:
- Раскладывай `<details>` блоком: summary выравнивай `text-align`, тело — блок ниже со своим `text-align: start`.
- Ширину задавай самому details в родительском flex (`flex-basis: 100%` в открытом состоянии через `[open]`).
- Признак: summary «растянулась» по высоте тела — details получил display:flex.
