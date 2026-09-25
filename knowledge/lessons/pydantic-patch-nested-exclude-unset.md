---
name: pydantic-patch-nested-exclude-unset
description: PATCH через model_dump(exclude_unset=True) срезает незаданные поля и во вложенных моделях — в базу пишется null вместо умолчаний; include=model_fields_set
stack: [fastapi]
status: candidate
created: 2026-09-24
seen_in: [video-blade-2]
triggers:
  keywords: [exclude_unset, patch, model_dump, вложенн, model_fields_set, pydantic, значения по умолчанию]
  commands: []
  errors: []
  paths: []
---
# PATCH и вложенные модели — include=model_fields_set, а не exclude_unset

Контекст: общий PATCH-обработчик писал `body.model_dump(exclude_unset=True)`. Новое вложенное поле-объект после
PATCH с одной координатой потеряло остальные ключи, а строки вложенных списков (ссылки, этапы, версии) получали
`null` там, где POST ставит значение по умолчанию.

Урок:
- `exclude_unset` работает рекурсивно: срезает незаданные поля и внутри вложенных моделей и строк списков.
- Для «меняем только присланные поля, но вложенное целиком» пиши `body.model_dump(include=body.model_fields_set)` —
  одно правило в общем обработчике, а не хак `model_post_init` в каждой вложенной модели.
- Признак: после PATCH во вложенном объекте пропал ключ или стоит `null` вместо умолчания, хотя POST того же тела
  даёт полное значение. Закрепи регрессионным тестом «PATCH-строка получает умолчания, как POST».
