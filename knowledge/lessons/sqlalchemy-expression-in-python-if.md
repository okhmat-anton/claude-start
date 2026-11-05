---
name: sqlalchemy-expression-in-python-if
description: Выражение SQLAlchemy (func.lower(User.email) == q) в питоновском if или списке не сравнивает значения и даёт ложь: в Python — поля объекта
stack: [python]
status: candidate
created: 2026-11-04
seen_in: [gym-bro-3]
triggers:
  keywords: [sqlalchemy, func.lower, BinaryExpression, фильтр в питоне, генератор списка, всегда ложно, не находит]
  commands: []
  errors: []
  paths: ['**/controllers/*.py']
---
# Выражение SQLAlchemy в питоновском условии не сравнивает значения

Контекст: поиск обещал «по почте — точное совпадение»; SQL находил человека, а фильтр видимости в Python
`if u.visibility == "all" or u.id in friends or func.lower(User.email) == q` отбрасывал его: справа выражение
SQLAlchemy, а не строка, и его `bool()` сравнивает сами выражения, а не значения — ложь. Тесты проверяли только
поиск по имени.

Урок:
- в питоновском условии — только поля объекта (`(u.email or "").lower() == q`), никогда колонки класса
  (`User.email`) и `func.*`: они строят SQL, а не считают;
- признак: `Model.` или `func.` внутри `if`, лямбды или генератора списка после `execute()`;
- каждая ветка `or` в фильтре — своим тестом: здесь падала бы только ветка «по почте».
