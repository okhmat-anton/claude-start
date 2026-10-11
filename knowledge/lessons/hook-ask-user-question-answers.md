---
name: hook-ask-user-question-answers
description: Хук PostToolUse(AskUserQuestion) читает выбор кнопками из tool_response — объект {questions, answers} или строка «"вопрос"="вариант"»; формат бери из стенограммы, не угадывай
index: Хук PostToolUse(AskUserQuestion): выбор кнопками приходит в tool_response объектом {answers} или строкой «"вопрос"="вариант"»; формат бери из стенограммы
stack: [any]
status: candidate
created: 2026-10-11
seen_in: [claude-start]
triggers:
  keywords: [AskUserQuestion, PostToolUse, tool_response, ответ кнопками, хук на вопрос, answers, стенограмм, transcript]
  commands: []
  errors: []
  paths: ['.claude/hooks/*', 'tools/hook.py']
---
# Ответ кнопками в хуке: формат из стенограммы, а не из головы

Контекст: хук на `PostToolUse(AskUserQuestion)` должен был записать выбранный владельцем вариант; документация формат
результата не описывает, а угадать его нельзя — в стенограмме он двух видов: поле записи `toolUseResult` несёт объект
`{"questions": [...], "answers": {"<вопрос>": "<подпись варианта>"}}`, а блок `tool_result` — строку
`Your questions have been answered: "<вопрос>"="<подпись>", … You can now continue…`.

Урок:
- Прежде чем писать хук или парсер под результат инструмента, достань реальный результат из стенограммы:
  `~/.claude/projects/<папка проекта>/<session>.jsonl` → `tool_use` с нужным именем → `tool_result` с тем же
  `tool_use_id` и поле `toolUseResult` той же записи. Скрипт на минуту вместо правок вслепую.
- Разбирай оба вида: словарь `answers`, иначе регулярка по парам `"q"="a"`; подпись варианта может нести хвост
  «(Recommended)» и свободный текст из «Other».
- Вопрос, к которому относится ответ, узнавай по `header` или тексту вопроса из `tool_input`, а не по порядку;
  непонятная подпись у одного вопроса не повод бросать разбор остальных.
