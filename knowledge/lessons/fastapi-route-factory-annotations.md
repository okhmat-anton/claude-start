---
name: fastapi-route-factory-annotations
description: Фабрика FastAPI-роутов при future annotations — класс тела проставлять в func.__annotations__ до регистрации, замыкание get_type_hints не резолвит
stack: [fastapi]
status: candidate
created: 2026-09-24
seen_in: [video-blade-2]
triggers:
  keywords: [fastapi, route factory, фабрика роутов, get_type_hints, future annotations, __future__, pydantic body, модель тела, валидация тела]
  commands: []
  errors: []
  paths: []
---
# Фабрика FastAPI-роутов при from __future__ import annotations — класс тела проставлять в func.__annotations__ до регистрации, замыкание get_type_hints не резолвит

Контекст: фабрика генерирует однотипные CRUD-роуты, класс pydantic-модели тела — параметр фабрики. В файле действует from __future__ import annotations: аннотации становятся строками, get_type_hints ищет имя в globals модуля и не находит переменную замыкания — тело запроса не резолвится (ошибка при регистрации или тип-«строка»).

Урок:
- В фабрике объявляй параметр тела без аннотации и до регистрации роута проставляй класс напрямую: func.__annotations__["body"] = model_in.
- Признак заранее: сочетание «future annotations + переменная-тип из замыкания в сигнатуре ручки» — оно не работает ни в FastAPI, ни в любом коде через get_type_hints.
- Альтернатива, если фабрика разрастается: убрать future-импорт из этого модуля целиком.
