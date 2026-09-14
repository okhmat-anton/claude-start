---
name: dev-vs-pinned-deps
description: Версии локально и в образе расходятся молча — dev-зависимости отдельно, рантайм по пинам; «импортируется» проверять пустым выводом, не по ModuleNotFoundError
stack: [python, any]
status: mature
created: 2026-08-04
seen_in: [ai-business-advisor-websites, 3d-printer]
triggers:
  keywords: [requirements, запинен, версия библиотеки, локально работает, в образе, ImportError, cannot import name, драйвер]
  commands: ['pip\s+install\s+(?!-r)', 'pip\s+install\s+-U', 'python3?\s+-c\s+.import']
  errors: ['ImportError: cannot import name', 'No module named']
  paths: ['requirements*.txt', 'pyproject.toml', 'Dockerfile']
---
# Версии локально и в образе расходятся молча

Контекст: на машине разработчика стоит то, что подтянулось последним, в образ ставится запиненное.
Расхождение не проявляется, пока тест не упрётся во внутреннее устройство или свежая версия драйвера не окажется
несовместима с запиненной обёрткой над ним (симптом — `ImportError` приватного имени, не `ModuleNotFoundError`).

Урок:
- Зависимости для разработки — отдельным файлом от рантаймовых; рантаймовые ставь по запиненным версиям,
  а не «последнее подходящее».
- «Модуль импортируется» проверяй по ПУСТОМУ выводу, а не по отсутствию строки `No module named`:
  `ImportError` из-за конфликта версий такую проверку проходит, и отчёт «всё импортируется» оказывается ложным.
