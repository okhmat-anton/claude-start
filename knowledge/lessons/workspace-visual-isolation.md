---
name: workspace-visual-isolation
description: Окно каждого проекта помечается тёмным приглушённым Peacock-цветом — нет .vscode/settings.json → создать, есть → не трогать; проверить занятые цвета
stack: [any]
status: mature
created: 2026-08-01
seen_in: [hr, planning]
triggers:
  keywords: [peacock, цвет окна, .vscode, settings.json, не тот проект, не в том окне, перепутал проект]
  commands: []
  errors: []
  paths: ['.vscode/settings.json']
---
# Визуальное различение окон редактора между проектами

Контекст: несколько одинаковых окон VS Code — правка уходит не в тот проект, команда запускается не в том
терминале; замечается после коммита.

Урок:
- В начале работы проверь `.vscode/settings.json`: нет — создай с Peacock-цветом; есть — не перезаписывай,
  цвет менять только по явной просьбе.
- Только тёмные приглушённые тона, оттенок под бренд проекта (мебель — орех, платежи — сине-серый). Status bar и
  title bar — тот же оттенок на 25–30 % темнее.
- Перед выбором проверь занятые цвета соседних проектов одной командой, иначе смысл теряется.
- Цвет применяется к окну, а не к папке: подпроект монорепо получит свой цвет, только если открыт отдельным окном.

```bash
find <projects-root> -maxdepth 3 -path "*/.vscode/settings.json" -not -path "*/node_modules/*" \
  | while read f; do echo "$f -> $(grep -o '"peacock.color": *"[^"]*"' "$f")"; done
```

Палитра: `#3C2A21` орех · `#2F3E46` сланец · `#293241` navy · `#3A2E39` слива · `#33413A` хвойный ·
`#3D3B30` олива · `#40312E` терракота · `#2B3A55` индиго.

```json
{ "peacock.color": "#2F3E46",
  "workbench.colorCustomizations": {
    "activityBar.background": "#2F3E46", "activityBar.foreground": "#e7e7e7", "activityBar.inactiveForeground": "#e7e7e799",
    "statusBar.background": "#232f35", "statusBar.foreground": "#e7e7e7",
    "titleBar.activeBackground": "#232f35", "titleBar.activeForeground": "#e7e7e7",
    "titleBar.inactiveBackground": "#232f3599", "titleBar.inactiveForeground": "#e7e7e799" },
  "peacock.affectedElements": ["activityBar", "statusBar", "titleBar"] }
```
