---
name: testclient-no-streaming-sse-test
description: Starlette TestClient не стримит: тест SSE-потока — укороти срок потока monkeypatch-ем и пиши событие из другого потока через client.portal.call
stack: [fastapi, python]
status: candidate
created: 2026-10-22
seen_in: [video-blade-2]
triggers:
  keywords: [TestClient, StreamingResponse, SSE, тест потока, event-stream, зависает тест, stream]
  commands: []
  errors: []
  paths: []
---
# Тест бесконечного SSE-потока в TestClient

Контекст: тест на ручку потока событий с TestClient висел — клиент отдаёт ответ целиком только после закрытия
потока, а поток живёт четверть часа и ждёт событий.

Урок:
- Срок жизни потока и интервал пинга — константы модуля; в тесте укороти их monkeypatch-ем до долей секунды:
  ответ закрывается сам и разбирается как обычное тело.
- Событие «во время» потока публикуй из другого потока исполнения через `client.portal.call(publish, …)`
  (портал anyio у TestClient), иначе запись попадёт до подписки или после закрытия.
- Проверяй кадры по тексту ответа (`retry:`, строки `data:`), а не по внутренностям хаба.
- Отдельно — модульный тест хаба без HTTP: подписка, слияние отметок, пропуск своего эха, лимиты.
