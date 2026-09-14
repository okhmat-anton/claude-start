---
name: multi-language-checks
description: make lint и make test покрывают каждый язык репозитория; «вторая команда руками» — источник пропусков; команда-проверка обязана существовать в зависимостях
stack: [any]
status: mature
created: 2026-07-26
seen_in: [jym-bro-2, ai-business-advisor, 3d-printer]
triggers:
  keywords: [make lint, make test, flutter analyze, npm run lint, второй язык, мультиязычн, запускать руками, не запускается команда]
  commands: ['\bflutter\s+(analyze|test)', 'npm\s+run\s+(lint|test)', '\bvue-tsc\b', '\btsc\b']
  errors: ['command not found: (eslint|vue-tsc|tsc|prettier)', 'npm ERR! missing script']
  paths: ['Makefile', 'package.json']
---
# Единая точка проверок покрывает все языки проекта

Контекст: `make lint`/`make test` гоняли только backend (ruff/pytest); анализатор и тесты клиента приходилось
помнить и запускать руками — при правках клиента их забывали и человек, и агент. В другом проекте
`package.json` содержал скрипт `lint`, ссылающийся на бинарь, которого нет ни в devDependencies, ни в lockfile.

Урок:
- Канонические цели проверок обязаны покрывать КАЖДЫЙ язык репозитория (ruff + flutter analyze, pytest +
  flutter test, eslint + vue-tsc). Появился первый тест или линтер во втором языке — в ту же минуту в общую цель.
- Первый widget-тест заводится вместе с первым пойманным UI-багом (регрессия), а не «когда-нибудь»; чтобы
  приватный виджет стал тестируемым, достаточно сделать его публичным.
- «Команда из правил не запускается» → сначала lockfile/devDependencies, а не чинить окружение. Инструмента
  нет = долг проекта (завести зависимость); до тех пор — документированная замена проверки (build + type-check
  по правленным файлам) с фиксацией замены в отчёте.
