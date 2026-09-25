---
name: mongo-naive-datetime-local-skew
description: Mongo отдаёт даты UTC без зоны — astimezone считает их местным временем машины; помечай UTC до перевода, тест с TZ не-UTC
stack: [python]
status: candidate
created: 2026-09-25
seen_in: [video-blade-2]
triggers:
  keywords: [naive datetime, astimezone, tzinfo, дата уехала, часовой пояс, pymongo, motor]
  commands: []
  errors: ["can't compare offset-naive and offset-aware datetimes"]
  paths: []
---
# Даты из Mongo приходят UTC без зоны — astimezone сдвигает их на пояс машины

Контекст: motor/pymongo по умолчанию отдают даты UTC без зоны; `value.astimezone(UTC)` считает наивную дату
местным временем машины. На сервере с TZ=UTC незаметно, на ноутбуке время в интерфейсе уезжает на пояс.

Урок:
- Наивную дату из Mongo сначала помечай UTC (`replace(tzinfo=UTC)`), потом переводи или форматируй.
- Регрессионный тест — с TZ не-UTC (`monkeypatch.setenv("TZ", …)` + `time.tzset()`), иначе на сервере баг
  не воспроизвести.
- Две даты из одного документа сравнивай как есть: обе наивные, смешивать их с aware нельзя.
