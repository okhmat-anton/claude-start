#!/usr/bin/env python3
"""Глобальные хуки Claude Code для базы знаний. Вызов: hook.py <event>, JSON хука на stdin.

  prompt         UserPromptSubmit — подмешать подходящие уроки; записать поправку владельца
  command        PreToolUse(Bash) — подмешать уроки по шаблону команды
  session-start  SessionStart — размер CLAUDE.md, неразобранные поправки, кандидаты в LESSONS.md
  stop           Stop — напомнить про retro, если правок много, а ретро не было

Хук никогда не блокирует работу: любая ошибка внутри — тихий выход 0.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knowledge as kb  # noqa: E402

SHOWN_DIR = Path.home() / ".claude" / "knowledge-shown"
CLAUDE_MD_MAX = int(os.environ.get("KNOWLEDGE_CLAUDE_MD_MAX", "80"))
RETRO_MIN_EDITS = int(os.environ.get("KNOWLEDGE_RETRO_MIN_EDITS", "5"))
CORRECTION_MARKERS = re.compile(
    r"(^|\s)(нет[,.!]|не так|не то[,.! ]|неправильно|опять|снова не|я же (говорил|писал|просил)|не надо было|"
    r"зачем ты|ты сломал|верни как было|откати|wrong|not what i|revert)",
    re.I,
)


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\s*$", re.S | re.M)


def strip_heredocs(cmd: str) -> str:
    """Тела heredoc — это содержимое файлов, а не команда: по ним уроки не подбираем."""
    return HEREDOC.sub("<<heredoc>", cmd)


def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def project_of(cwd: str) -> tuple[Path, str, list[str]]:
    root = Path(cwd or os.getcwd())
    name = root.name
    stack: list[str] = []
    cfg = root / ".claude" / "knowledge.json"
    if cfg.exists():
        try:
            stack = [str(s) for s in json.loads(cfg.read_text(encoding="utf-8")).get("stack", [])]
        except (json.JSONDecodeError, OSError):
            pass
    return root, name, stack


def shown_set(session: str) -> tuple[Path, set[str]]:
    SHOWN_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().timestamp()
    for f in SHOWN_DIR.glob("*.json"):
        try:
            if now - f.stat().st_mtime > 2 * 86400:
                f.unlink()
        except OSError:
            pass
    f = SHOWN_DIR / f"{session or 'nosession'}.json"
    try:
        return f, set(json.loads(f.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return f, set()


def remember_shown(f: Path, shown: set[str], names: list[str], project: str) -> None:
    shown.update(names)
    try:
        f.write_text(json.dumps(sorted(shown)), encoding="utf-8")
    except OSError:
        pass
    try:
        kb.record_usage(names, "shown", project)
    except OSError:
        pass


# --------------------------------------------------------------------------- events


def on_prompt(inp: dict) -> None:
    prompt = str(inp.get("prompt") or "")
    root, project, stack = project_of(inp.get("cwd", ""))
    # 1. поправка владельца → журнал для retro
    if (root / ".claude").is_dir() and CORRECTION_MARKERS.search(prompt) and len(prompt) < 2000:
        log = root / ".claude" / "corrections.log"
        excerpt = " ".join(prompt.split())[:240]
        try:
            with log.open("a", encoding="utf-8") as fh:
                fh.write(f"{dt.date.today().isoformat()} | {excerpt}\n")
        except OSError:
            pass
    # 2. подходящие уроки
    if len(prompt) < 25:
        return
    f, shown = shown_set(str(inp.get("session_id", "")))
    res = kb.match(prompt=prompt, stack=stack, limit=3, threshold=3, exclude=shown)
    if not res:
        return
    print("Из общей базы знаний, по теме запроса (применил — отметь в retro через knowledge.py hit):")
    for u, _, _ in res:
        print(kb.render_hint(u, full=True))
    remember_shown(f, shown, [u.name for u, _, _ in res], project)


def on_command(inp: dict) -> None:
    if inp.get("tool_name") != "Bash":
        return
    cmd = strip_heredocs(str((inp.get("tool_input") or {}).get("command") or ""))
    if not cmd or len(cmd) > 1500:  # длинная команда — это запись файла, не действие
        return
    root, project, stack = project_of(inp.get("cwd", ""))
    f, shown = shown_set(str(inp.get("session_id", "")))
    res = kb.match(command=cmd, stack=stack, limit=2, threshold=4, exclude=shown, use_keywords=False)
    if not res:
        return
    text = "Из базы знаний, по этой команде:\n" + "\n".join(kb.render_hint(u, full=False, max_lines=14) for u, _, _ in res)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}, ensure_ascii=False))
    remember_shown(f, shown, [u.name for u, _, _ in res], project)


def on_session_start(inp: dict) -> None:
    root, _, _ = project_of(inp.get("cwd", ""))
    notes: list[str] = []
    for name in ("CLAUDE.md", "Claude.md"):
        p = root / name
        if p.exists():
            n = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
            if n > CLAUDE_MD_MAX:
                notes.append(f"{name}: {n} строк при норме 60. Процедуры и карты файлов вынеси в .claude/skills/ и .claude/rules/, оставь только постоянные факты.")
            break
    log = root / ".claude" / "corrections.log"
    if log.exists():
        lines = [ln for ln in log.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip() and not ln.startswith("#")]
        if lines:
            notes.append(f"Поправок владельца, не разобранных в retro: {len(lines)} (см. .claude/corrections.log). Retro превращает их в уроки и очищает файл.")
    lessons = root / "LESSONS.md"
    if lessons.exists():
        txt = lessons.read_text(encoding="utf-8", errors="ignore")
        unsent = len(re.findall(r"Повторений:\**\s*1\b", txt))
        if unsent >= 8:
            notes.append(f"В LESSONS.md {unsent} незрелых уроков. Зрелость считается по проектам, а не по повторам внутри одного: отправь их кандидатами в базу знаний (skill knowledge-sync).")
    if notes:
        print("Система самообучения:\n- " + "\n- ".join(notes))


def _iter_tool_uses(transcript: Path):
    try:
        with transcript.open(encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                content = msg.get("content") if isinstance(msg, dict) else None
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        yield block.get("name") or "", block.get("input") or {}
    except OSError:
        return


def on_stop(inp: dict) -> None:
    if inp.get("stop_hook_active"):
        return
    root, _, _ = project_of(inp.get("cwd", ""))
    if not (root / "LESSONS.md").exists():
        return
    session = str(inp.get("session_id") or "nosession")
    marker = root / ".claude" / f".retro-prompted-{session}"
    if marker.exists():
        return
    transcript = Path(str(inp.get("transcript_path") or ""))
    if not transcript.exists():
        return
    edits, files, retro_done = 0, set(), False
    journal = ("LESSONS.md", "simplify-memory.md", "DECISIONS.md")
    for name, tin in _iter_tool_uses(transcript):
        if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            fp = str(tin.get("file_path") or tin.get("notebook_path") or "")
            if any(fp.endswith(j) for j in journal):
                retro_done = True
            else:
                edits += 1
                files.add(fp)
        elif name == "Skill" and str(tin.get("skill") or "") in ("retro", "knowledge-sync"):
            retro_done = True
        elif name == "Bash" and "knowledge.py hit" in str(tin.get("command") or ""):
            retro_done = True
    if retro_done or edits < RETRO_MIN_EDITS:
        return
    try:
        marker.parent.mkdir(exist_ok=True)
        marker.write_text(dt.datetime.now().isoformat(), encoding="utf-8")
    except OSError:
        pass
    reason = (
        f"Контроль самообучения: в сессии {edits} правок в {len(files)} файлах, а retro не запускалось. "
        "Прогони skill retro (три вопроса: что пошло не так; что вышло быстрее ожидаемого и почему; "
        "где владелец поправил — см. .claude/corrections.log). Урок есть — запиши и отправь кандидатом в базу знаний; "
        "уроков нет — скажи это одной строкой и завершай."
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    inp = read_input()
    try:
        {"prompt": on_prompt, "command": on_command, "session-start": on_session_start, "stop": on_stop}.get(event, lambda _: None)(inp)
    except Exception as ex:  # noqa: BLE001 — хук не должен ронять работу
        print(f"knowledge hook '{event}' failed: {ex}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
