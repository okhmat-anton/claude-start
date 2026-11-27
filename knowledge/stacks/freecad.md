---
name: freecad
description: FreeCAD без окна на macOS — установка brew cask, путь к freecadcmd, встроенный Python 3.11 (линтер py311), импорт FreeCAD/Part, проверка кубом
stack: [freecad, python]
triggers:
  keywords: [freecad, freecadcmd, FCStd, чертеж, модель детали, Part.makeBox, параметрическ, CAD]
  commands: ['freecadcmd', 'brew\s+install\s+--cask\s+freecad']
  errors: []
  paths: ['**/*.FCStd', '**/*.FCMacro']
---
# FreeCAD без окна — модели скриптами (macOS, FreeCAD 1.1)

- Установка: `brew install --cask freecad` — около 3 минут и 1–2 ГБ, ставит `/Applications/FreeCAD.app`;
  проверено 11.2026 на FreeCAD 1.1.4 (Apple Silicon). Запуск из терминала Gatekeeper не блокирует.
- Без окна: `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd <скрипт.py>`. В PATH его нет — путь
  целиком; рядом лежат `freecad` (окно) и `python` (встроенный).
- Встроенный Python — 3.11, свой, не системный: `import FreeCAD, Part` работает только в нём, в venv проекта эти
  модули не импортируются. Линтеру скриптов моделей — `target-version = "py311"`, иначе пропустит синтаксис новее.
- Проверка установки за секунду: скрипт с `Part.makeBox(10, 10, 10)` печатает `box.Volume` (ждём 1000.0) и
  `FreeCAD.Version()`; код возврата 0.
- `print` скрипта идёт в stdout вперемешку с баннером версии — нужные строки фильтруй, статус бери по коду возврата.
- Агенту удобно так: параметры модели (размеры в мм, допуски) — константами наверху скрипта, `.FCStd` собирается
  из скрипта; правку человека в окне FreeCAD переносить обратно в параметры, а не править `.FCStd` руками.
