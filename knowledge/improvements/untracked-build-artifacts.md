---
name: untracked-build-artifacts
description: Кэш интерпретатора и служебные файлы ОС не отслеживаются git — .gitignore и снятие с учёта, иначе каждый прогон пачкает копии и клоны
kind: module
stack: [any]
status: mature
created: 2026-10-21
seen_in: [claude-start, akm-news]
benefit: 4
rating: 5
triggers:
  keywords: [__pycache__, .pyc, .DS_Store, gitignore, git status грязн, незакоммиченн]
  commands: []
  errors: []
  paths: ['.gitignore', '**/__pycache__/*', '*.pyc']
---
# Служебные файлы не отслеживаются git

Когда: в `git status` после обычной работы (тесты, хуки, открытие папки) появляются изменённые файлы, которых никто
не правил: кэш интерпретатора (`__pycache__/*.pyc`), `.DS_Store`, сборочные артефакты; `.gitignore` нет или он их не знает.

Предложение: добавить их в `.gitignore` и снять с учёта (`git rm -r --cached`), не удаляя с диска. Делаем?

Выгода: чистый `git status`, коммиты «только своих путей» без лишних файлов, нет ложных конфликтов при `pull --rebase`
в клонах. Цена: две строки в `.gitignore` и одна команда, ~2 минуты.
