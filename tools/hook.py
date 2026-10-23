#!/usr/bin/env python3
"""Глобальные хуки Claude Code для базы знаний. Вызов: hook.py <event>, JSON хука на stdin.

  prompt         UserPromptSubmit — подмешать подходящие уроки; записать поправку владельца;
                 уровень задачи назван в промте — записать; не назван, а промт похож на задачу — записать
                 «простая» по умолчанию и напомнить перепроверить (не простая — предложить кнопками)
  command        PreToolUse(Bash) — подмешать уроки по шаблону команды
  ask            PostToolUse(AskUserQuestion) — записать уровень задачи, выбранный кнопками
  session-start  SessionStart — размер CLAUDE.md, неразобранные поправки, кандидаты в LESSONS.md, уровень задачи,
                 улучшения из базы, не решённые в проекте
  stop           Stop — напомнить про retro, если правок много, а ретро не было (не в простой и средней задаче)

Уровень задачи (простая / средняя / сложная) лежит в ~/.claude/task-tier/<session_id>.json — правило владельца
(11.10.2026): глубину ревью, упрощения и уроков выбирает он, словом в промте или кнопками до начала работы.
Уточнение 12.10.2026: уровень не назван — по умолчанию простая; агент перепроверяет и, если задача не простая,
предлагает выбор кнопками, а не назначает уровень сам.

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

# --------------------------------------------------------------------------- уровень задачи

TIER_DIR = Path.home() / ".claude" / "task-tier"
TIERS = {"simple": "простая", "medium": "средняя", "complex": "сложная"}
TIER_PROTOCOL = {
    "simple": "сделать → тесты и линт → коммит и push; без разбора, плана, ревью, упрощения и retro",
    "medium": "краткий разбор → план → правки → самопроверка → 1 круг урезанного ревью → упрощение только по диффу, "
    "улучшения по модулю → done-check → коммит; без retro",
    "complex": "полный разбор → план → правки → самопроверка → до 3 кругов взгляда Джобса → упрощение по файлам и "
    "окружению, улучшения по модулю → done-check → коммит → retro и knowledge-sync",
}
_TIER_WORDS = {  # единственное число: «сложные задачи у нас долгие» — не уровень; «средней сложности» — средняя
    "medium": r"средн(?:яя|юю|ей)(?:\s+сложност\w*)?",
    "simple": r"прост(?:ая|ую|ой)",
    "complex": r"сложн(?:ая|ую|ой)",
}
# Слово уровня само по себе ничего не значит («сделай простую форму», «Сложная формула считает неверно») —
# только с якорем: первое слово промта с разделителем после него, метка [..]/#.., рядом со словом «задача»,
# после «сложность:» / «уровень —». Английское слово — только первым с разделителем, меткой или после «tier:».
_TIER_ANCHORS = (
    r"\A\s*[\[\(#]?\s*(?:{w}|{en})[ \t]*(?:[:—\-,.!\]\)\n]|\Z)",
    r"[\[#](?:{w}|{en})\b",
    r"\b(?:{w})\s+(?:по\s+сложности\s+)?задач",
    r"\bзадач\w*\s*(?:[—:\-]\s*)?(?:{w})\b",
    r"\b(?:сложност\w*|уровень|complexity|tier)\s*[:—\-]?\s*(?:{w}|{en})\b",
)
TIER_RE = {t: re.compile("|".join(a.format(w=w, en=t) for a in _TIER_ANCHORS), re.I) for t, w in _TIER_WORDS.items()}  # ключ = английское слово
# Промт похож на задачу с правками: глагол в повелительном наклонении или инфинитиве целым словом
# («удали», но не «удалённый»; «add», но не «addresses»); вопрос («…?») задачей не считается.
TASK_VERBS = re.compile(
    r"\b(?:сдела(?:й|ть)|добав(?:ь|ить)|исправ(?:ь|ить)|поправ(?:ь|ить)|почин(?:и|ить)|напиш(?:и)|написать|"
    r"реализ(?:уй|овать)|внедр(?:и|ить)|передел(?:ай|ать)|убер(?:и)|убрать|замен(?:и|ить)|созда(?:й|ть)|"
    r"настро(?:й|ить)|перенес(?:и|ти)|обнов(?:и|ить)|доработа(?:й|ть)|допиш(?:и)|дописать|вынес(?:и|ти)|"
    r"удал(?:и|ить)|перепиш(?:и)|переписать|постро(?:й|ить)|собер(?:и)|собрать|подключ(?:и|ить)|прикрут(?:и|ить)|"
    r"fix|add|implement|refactor|build|create|rewrite|remove)\b",
    re.I,
)
QUESTION = re.compile(r"\?|\A\s*(?:как|почему|зачем|что|где|когда|какой|какая|какие|сколько|можно ли|why|how|what|where)\b", re.I)


def looks_like_task(prompt: str) -> bool:
    """Промт с глаголом правки и без признаков вопроса — повод напомнить про уровень; это подсказка, не решение."""
    return len(prompt) >= 25 and not QUESTION.search(prompt) and bool(TASK_VERBS.search(prompt))


def detect_tier(prompt: str) -> str | None:
    """Уровень, названный в промте; None — не назван или назван двусмысленно (в обоих случаях — спросить)."""
    found = [t for t, rx in TIER_RE.items() if rx.search(prompt)]
    return found[0] if len(found) == 1 else None


def tier_of_label(label: str) -> str | None:
    """Уровень из подписи кнопки («Средняя (Recommended)», «сложная, но без retro»); два уровня в подписи — None."""
    found = [t for t, pat in (("medium", r"средн|medium"), ("simple", r"прост|simple"), ("complex", r"сложн|complex"))
             if re.search(pat, label, re.I)]
    return found[0] if len(found) == 1 else None


def _tier_file(session: str) -> Path:
    return _session_file(TIER_DIR, session, ttl_days=14)  # дольше, чем показы уроков: сессию возобновляют и через неделю


def load_tier(session: str) -> dict:
    try:
        return json.loads(_tier_file(session).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_tier(session: str, tier: str, source: str, project: str) -> None:
    rec = {"tier": tier, "source": source, "project": project, "at": dt.datetime.now().isoformat(timespec="seconds")}
    try:
        _tier_file(session).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def tier_line(tier: str, how: str) -> str:
    return (f"Уровень задачи: {TIERS[tier]} ({how}). Протокол: {TIER_PROTOCOL[tier]}. "
            "Ход задач (skill task-log): записи ещё нет — заведи сейчас; этапы отмечай по ходу, закрой в конце.")


TIER_SOURCE_HOW = {"prompt": "назван в промте", "buttons": "выбран кнопками", "default": "по умолчанию"}
RECHECK = (
    "Перепроверь (skill task-tier): новый экран или окно, несколько модулей или больше 3–4 файлов, деньги, доступ "
    "или данные, неясные требования — тогда не назначай уровень сам, а предложи владельцу кнопками простая / "
    "средняя / сложная, свою оценку первым вариантом. Признаков нет — назови одной строкой «Уровень: простая "
    "(по умолчанию)» и делай. Вопрос, уточнение по текущей задаче или ответ на твой вопрос — уровень не трогай."
)


def resolve_tier(prompt: str, saved: dict) -> tuple[str | None, str | None, str]:
    """(уровень для записи, его источник, строка агенту) по промту и записи сессии; уровень None — не писать.

    Назван в промте — он и пишется. Не назван, а промт похож на задачу — «простая» по умолчанию, но уровень,
    названный раньше в промте или выбранный кнопками, не перезаписывается: хук не отличает новую задачу от
    уточнения по текущей, а молча потерять «сложная» дороже, чем лишний раз напомнить.
    """
    tier = detect_tier(prompt)
    if tier:
        return tier, "prompt", tier_line(tier, TIER_SOURCE_HOW["prompt"])
    if not looks_like_task(prompt):
        return None, None, ""
    prev = saved.get("tier")
    if prev in TIERS and saved.get("source") != "default":
        return None, None, (
            f"Уровень текущей задачи: {TIERS[prev]} (задан ранее в этой сессии). Это новая задача, а не уточнение "
            f"по текущей — уровень определяется заново: по умолчанию простая. {RECHECK}"
        )
    return "simple", "default", f"{tier_line('simple', TIER_SOURCE_HOW['default'] + ': в промте не назван')} {RECHECK}"


def strip_heredocs(cmd: str) -> str:
    """Тела heredoc — это содержимое файлов, а не команда: по ним уроки не подбираем."""
    return HEREDOC.sub("<<heredoc>", cmd)


def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


TEMP_ROOTS = ("/tmp/", "/private/tmp/", "/var/folders/")


def is_project(root: Path) -> bool:
    """Проект — папка со своим .claude/ или корнем git. Временные папки и рабочие копии в scratchpad проектом
    не считаются: иначе их имена оседают в статистике usage.json (решение владельца, 21.10.2026)."""
    if "scratchpad" in root.parts or f"{root}/".startswith(TEMP_ROOTS):
        return False
    return (root / ".claude").is_dir() or (root / ".git").exists()


def project_of(cwd: str) -> tuple[Path, str, list[str]]:
    root = Path(cwd or os.getcwd())
    name = root.name if is_project(root) else ""
    stack: list[str] = []
    cfg = root / ".claude" / "knowledge.json"
    if cfg.exists():
        try:
            stack = [str(s) for s in json.loads(cfg.read_text(encoding="utf-8")).get("stack", [])]
        except (json.JSONDecodeError, OSError):
            pass
    return root, name, stack


def _session_file(d: Path, session: str, ttl_days: int = 2) -> Path:
    """Файл этой сессии в папке d; файлы старше ttl_days убираются по пути."""
    d.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().timestamp()
    for f in d.glob("*.json"):
        try:
            if now - f.stat().st_mtime > ttl_days * 86400:
                f.unlink()
        except OSError:
            pass
    return d / f"{session or 'nosession'}.json"


def shown_set(session: str) -> tuple[Path, set[str]]:
    f = _session_file(SHOWN_DIR, session)
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
    # 2. уровень задачи: назван — записать; не назван, а промт похож на задачу — «простая» по умолчанию и напомнить
    #    перепроверить (не простая — предложить кнопками)
    session = str(inp.get("session_id", ""))
    tier, source, line = resolve_tier(prompt, load_tier(session))
    if tier and source:
        save_tier(session, tier, source, project)
    if line:
        print(line)
    # 3. подходящие уроки
    if len(prompt) < 25:
        return
    f, shown = shown_set(session)
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


def _answers(tool_response) -> list[tuple[str, str]]:
    """Пары (вопрос, выбранный вариант) из результата AskUserQuestion: объект с answers или строка «"q"="a"»."""
    if isinstance(tool_response, dict) and isinstance(tool_response.get("answers"), dict):
        return [(str(q), str(a)) for q, a in tool_response["answers"].items()]
    text = tool_response if isinstance(tool_response, str) else json.dumps(tool_response, ensure_ascii=False)
    return re.findall(r'"((?:[^"\\]|\\.)*)"="((?:[^"\\]|\\.)*)"', text)


def on_ask(inp: dict) -> None:
    if inp.get("tool_name") != "AskUserQuestion":
        return
    tin = inp.get("tool_input") or {}
    about_tier = re.compile(r"сложност|уровень задач|complexity|tier", re.I)
    tier_questions = {
        str(q.get("question"))
        for q in (tin.get("questions") or [])
        if isinstance(q, dict) and about_tier.search(str(q.get("header") or ""))
    }
    for question, label in _answers(inp.get("tool_response")):
        if question not in tier_questions and not about_tier.search(question):
            continue
        tier = tier_of_label(label)
        if not tier:
            continue
        _, project, _ = project_of(inp.get("cwd", ""))
        save_tier(str(inp.get("session_id", "")), tier, "buttons", project)
        out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": tier_line(tier, TIER_SOURCE_HOW["buttons"] + ", записан")}}
        print(json.dumps(out, ensure_ascii=False))
        return


def on_session_start(inp: dict) -> None:
    root, project, stack = project_of(inp.get("cwd", ""))
    notes: list[str] = []
    t = load_tier(str(inp.get("session_id", "")))
    if t.get("tier") in TIERS:
        notes.append(tier_line(t["tier"], TIER_SOURCE_HOW.get(str(t.get("source")), "выбран") + " ранее в этой сессии"))
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
    if project and (root / ".claude" / "knowledge.json").exists():  # база подключена — напомнить про улучшения, не решённые здесь
        pending = len(kb.improvements(project=project, stack=stack))
        if pending:
            notes.append(f"В базе улучшений {pending} не решённых в этом проекте — прогнать по слову владельца: skill improve-sweep.")
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
    if load_tier(session).get("tier") in ("simple", "medium"):
        return  # по уровню задачи уроки не пишутся — напоминать про retro нечего
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
        handlers = {"prompt": on_prompt, "command": on_command, "ask": on_ask, "session-start": on_session_start, "stop": on_stop}
        handlers.get(event, lambda _: None)(inp)
    except Exception as ex:  # noqa: BLE001 — хук не должен ронять работу
        print(f"knowledge hook '{event}' failed: {ex}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
