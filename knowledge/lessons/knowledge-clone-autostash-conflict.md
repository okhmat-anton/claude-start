---
name: knowledge-clone-autostash-conflict
description: Незакоммиченная правка в клоне базы знаний (style-base) при следующем pull — конфликт автостэша: слить обе стороны, stash drop, правила коммитить в конце задачи
stack: [any]
status: candidate
created: 2026-10-23
seen_in: [tech]
triggers:
  keywords: [autostash, конфликт, клон базы, style-base, незакоммичен, stash]
  commands: ['git pull --rebase --autostash', 'git -C .*knowledge-repo.* pull', 'git stash (pop|drop)']
  errors: ['Applying autostash resulted in conflicts', 'CONFLICT \(content\)']
  paths: ['knowledge/skills/style-base/*']
---
# Незакоммиченная правка в клоне базы при следующем pull становится конфликтом автостэша

Контекст: правило базы стиля дописали в клоне общей базы знаний и не закоммитили в конце задачи; через два дня
/start другого проекта сделал `git pull --rebase --autostash`, upstream успел измениться в том же разделе —
«Applying autostash resulted in conflicts», в файле маркеры `<<<<<<< Updated upstream`, своя правка — в stash.

Урок:
- Правило базы стиля или урок, дописанный в клоне, коммить и пушь в конце той же задачи (knowledge-sync), а не
  «потом»: `git status --short` клона перед `pull` не должен показывать ` M`.
- Конфликт автостэша в файле-списке правил решай слиянием обеих сторон — нужны и строки upstream, и своя: убери
  маркеры, `git restore --staged <файл>`, проверь `grep -c '^<<<<<<<' <файл>` = 0, затем `git stash drop`.
- Признак заранее: ` M knowledge/skills/style-base/SKILL.md` в `git status` клона или слово autostash в выводе pull.
- Правку не откатывай через `git checkout --`: она не в коммитах, только в stash, и потеряется.
