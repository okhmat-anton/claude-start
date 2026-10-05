---
name: agent-instruction-code-must-run
description: Код из инструкции для агента исполняй на чистой машине: urllib на macOS (python.org) падает без корневых сертификатов и URLError
stack: [llm]
status: candidate
created: 2026-10-05
seen_in: [video-blade-2]
triggers:
  keywords: [протокол, CERTIFICATE_VERIFY_FAILED, urllib, python.org, инструкци]
  commands: []
  errors: ['CERTIFICATE_VERIFY_FAILED']
  paths: []
---
# Код из инструкции для агента исполняй на чистой машине: urllib на macOS (python.org) падает без корневых сертификатов и URLError

Контекст: инструкция для стороннего агента содержала «готовый клиент на стандартной библиотеке». На машине
пользователя он падал трассировкой на первом запросе: сборка Python с python.org для macOS идёт без корневых
сертификатов, а клиент ловил только HTTP-ошибки.

Урок:
- Код из инструкции исполняй сам, на чистой машине и не тем интерпретатором, которым разрабатываешь, — читать мало.
- Клиент на urllib: если у Python нет своих сертификатов (`ssl.get_default_verify_paths()` без cafile и capath),
  бери системный набор `/etc/ssl/cert.pem`; `URLError` лови отдельно и отвечай одной строкой.
- Регрессия: тест вынимает блок кода из инструкции, запускает его и проверяет оба случая.
