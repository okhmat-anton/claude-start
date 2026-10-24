---
name: run-once-objects-recreate-per-lifespan
description: Объект, который запускается один раз на экземпляр (менеджер сессий SDK), создаётся в lifespan, не при импорте: тесты стартуют приложение на каждый прогон
stack: [fastapi]
status: candidate
created: 2026-10-23
seen_in: [video-blade-2]
triggers:
  keywords: [lifespan, TestClient, run once, менеджер сессий, task group, повторный запуск, второй тест]
  commands: ['pytest']
  errors: ['can only be called once', 'Task group is not initialized', 'already (started|running)']
  paths: ['app/main.py']
---
# Объект с запуском «один раз на экземпляр» создаётся в lifespan, не при импорте: тесты стартуют приложение на каждый прогон

Контекст: приложение SDK и его менеджер сессий были созданы на уровне модуля, а `session_manager.run()` вызывался
в lifespan. Первый тест прошёл, следующий TestClient снова вошёл в lifespan — RuntimeError, девять тестов упали на setup.

Урок:
- Всё, что документация называет «один раз на экземпляр» (менеджеры сессий, пулы, task group), создавай внутри
  lifespan и подменяй в обёртке маршрута; на уровне модуля держи только обёртку.
- Признак: ошибка повторного запуска появляется со второго теста, а в одиночном прогоне всё зелёное.
