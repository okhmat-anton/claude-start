#!/bin/bash
# Подключает глобальные хуки и скиллы базы знаний к ~/.claude. Идемпотентно.
set -euo pipefail
KB="$(cd "$(dirname "$0")/.." && pwd)"
SETTINGS="$HOME/.claude/settings.json"
mkdir -p "$HOME/.claude/skills"

KB="$KB" SETTINGS="$SETTINGS" python3 - <<'PY'
import json, os
kb, path = os.environ["KB"], os.environ["SETTINGS"]
hook = lambda ev: f'python3 "{kb}/tools/hook.py" {ev}'
want = {
    "UserPromptSubmit": (None, hook("prompt"), 10),
    "PreToolUse": ("Bash", hook("command"), 10),
    "SessionStart": (None, hook("session-start"), 10),
    "Stop": (None, hook("stop"), 15),
}
data = {}
if os.path.exists(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
hooks = data.setdefault("hooks", {})
changed = 0
for event, (matcher, cmd, timeout) in want.items():
    entries = hooks.setdefault(event, [])
    # убрать старые версии этого же хука (другой путь клона), оставить чужие
    for e in entries:
        e["hooks"] = [h for h in e.get("hooks", []) if "tools/hook.py" not in h.get("command", "") or h["command"] == cmd]
    entries[:] = [e for e in entries if e.get("hooks")]
    if any(h.get("command") == cmd for e in entries for h in e.get("hooks", [])):
        continue
    entry = {"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]}
    if matcher:
        entry["matcher"] = matcher
    entries.append(entry)
    changed += 1
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(f"hooks: добавлено {changed}, всего событий подключено {len(want)} → {path}")
PY

for skill in "$KB"/knowledge/skills/*/SKILL.md; do
  dir="$(dirname "$skill")"; name="$(basename "$dir")"
  if grep -q '^scope: global' "$skill"; then
    ln -sfn "$dir" "$HOME/.claude/skills/$name"
    echo "skill (global): $name → ~/.claude/skills/$name"
  fi
done
python3 "$KB/tools/knowledge.py" lint >/dev/null && echo "lint: ок" || echo "lint: есть замечания — python3 tools/knowledge.py lint"
echo "готово. Проверка: echo '{\"prompt\":\"файлы падают в корень репо, command not found\"}' | python3 $KB/tools/hook.py prompt"
