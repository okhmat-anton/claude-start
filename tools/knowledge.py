#!/usr/bin/env python3
"""Инструмент базы знаний claude-start. Только стандартная библиотека.

Команды:
  lint                  проверить формат всех единиц знания
  index                 пересобрать knowledge/INDEX.md из шапок файлов
  match                 подобрать единицы под промт / команду / файлы (для хуков)
  hit <name>            отметить, что урок реально применён (счётчик в usage.json)
  new <name> ...        создать каркас новой единицы в правильном формате
  gc                    отчёт для уборки: дубли, протухшее, кандидаты на зрелость
  stats                 сводка по базе
  show <name>           напечатать единицу
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "knowledge"
USAGE = KB / "usage.json"
KINDS = {"lessons": "lesson", "stacks": "stack", "skills": "skill"}
STATUSES = {"candidate", "mature", "archived"}
DESC_MAX = 160
PROSE_MAX = 30
TRIGGER_KEYS = ("keywords", "commands", "errors", "paths")

# --------------------------------------------------------------------------- yaml-lite


def _split_flow(s: str) -> list[str]:
    """'[a, "b, c", 'd']' -> ['a', 'b, c', 'd']"""
    s = s.strip()
    if not (s.startswith("[") and s.endswith("]")):
        return [_unquote(s)] if s else []
    s = s[1:-1]
    out, buf, q = [], "", None
    for ch in s:
        if q:
            if ch == q:
                q = None
            else:
                buf += ch
        elif ch in "'\"":
            q = ch
        elif ch == ",":
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    head = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")
    data: dict = {}
    cur_key = None
    for raw in head.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            if line.startswith("- ") and cur_key:
                data.setdefault(cur_key, [])
                if isinstance(data[cur_key], list):
                    data[cur_key].append(_unquote(line[2:]))
                continue
            key, _, val = line.partition(":")
            cur_key = key.strip()
            val = val.strip()
            if val == "":
                data[cur_key] = {}
            elif val.startswith("["):
                data[cur_key] = _split_flow(val)
            else:
                data[cur_key] = _unquote(val)
        else:
            if cur_key is None:
                continue
            if line.startswith("- "):
                if isinstance(data.get(cur_key), dict) and data[cur_key].get("__last"):
                    sub = data[cur_key]["__last"]
                    data[cur_key].setdefault(sub, [])
                    data[cur_key][sub].append(_unquote(line[2:]))
                else:
                    if not isinstance(data.get(cur_key), list):
                        data[cur_key] = []
                    data[cur_key].append(_unquote(line[2:]))
                continue
            key, _, val = line.partition(":")
            if not isinstance(data.get(cur_key), dict):
                data[cur_key] = {}
            val = val.strip()
            data[cur_key][key.strip()] = _split_flow(val) if val.startswith("[") else (_unquote(val) if val else [])
            data[cur_key]["__last"] = key.strip()
    for v in data.values():
        if isinstance(v, dict):
            v.pop("__last", None)
    return data, body


# --------------------------------------------------------------------------- units


class Unit:
    def __init__(self, path: Path):
        self.path = path
        self.rel = path.relative_to(KB).as_posix()
        self.kind = KINDS.get(path.relative_to(KB).parts[0], "other")
        text = path.read_text(encoding="utf-8")
        self.meta, self.body = parse_frontmatter(text)
        self.has_frontmatter = bool(self.meta)
        self.name = str(self.meta.get("name") or path.stem if self.kind != "skill" else self.meta.get("name") or path.parent.name)
        self.description = str(self.meta.get("description") or "")
        self.index_line = str(self.meta.get("index") or self.description)
        self.stack = _as_list(self.meta.get("stack")) or ["any"]
        self.status = str(self.meta.get("status") or ("mature" if self.kind != "lesson" else ""))
        self.seen_in = _as_list(self.meta.get("seen_in"))
        self.created = str(self.meta.get("created") or "")
        self.scope = str(self.meta.get("scope") or "project")
        trig = self.meta.get("triggers") or {}
        self.triggers = {k: _as_list(trig.get(k)) for k in TRIGGER_KEYS} if isinstance(trig, dict) else {k: [] for k in TRIGGER_KEYS}

    # prose lines: without fenced code, tables, blank lines
    def prose_lines(self) -> int:
        n, fenced = 0, False
        for line in self.body.splitlines():
            s = line.strip()
            if s.startswith("```"):
                fenced = not fenced
                continue
            if fenced or not s or s.startswith("|") or s.startswith("<!--"):
                continue
            n += 1
        return n

    def title(self) -> str:
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return self.name

    def age_days(self, today: dt.date | None = None) -> int | None:
        if not self.created:
            return None
        try:
            return ((today or dt.date.today()) - dt.date.fromisoformat(self.created)).days
        except ValueError:
            return None


def _as_list(v) -> list[str]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def load_units(kinds=("lessons", "stacks", "skills")) -> list[Unit]:
    units = []
    for d in kinds:
        base = KB / d
        if not base.exists():
            continue
        files = sorted(base.glob("*/SKILL.md")) if d == "skills" else sorted(base.glob("*.md"))
        for f in files:
            units.append(Unit(f))
    return units


def find_unit(name: str) -> Unit | None:
    for u in load_units():
        if u.name == name:
            return u
    return None


# --------------------------------------------------------------------------- usage


def load_usage() -> dict:
    if USAGE.exists():
        try:
            return json.loads(USAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_usage(data: dict) -> None:
    tmp = USAGE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, USAGE)


def record_usage(names: list[str], field: str, project: str | None) -> None:
    if not names:
        return
    data = load_usage()
    today = dt.date.today().isoformat()
    for n in names:
        rec = data.setdefault(n, {"shown": 0, "applied": 0, "projects": {}})
        rec[field] = rec.get(field, 0) + 1
        rec["last_" + field] = today
        if project:
            p = rec.setdefault("projects", {})
            p[project] = p.get(project, 0) + (1 if field == "applied" else 0)
    save_usage(data)


# --------------------------------------------------------------------------- lint


def lint(units: list[Unit] | None = None) -> list[str]:
    units = units or load_units()
    errors: list[str] = []
    names: dict[str, str] = {}
    for u in units:
        e = lambda msg: errors.append(f"{u.rel}: {msg}")  # noqa: E731
        if not u.has_frontmatter:
            e("нет шапки (frontmatter)")
            continue
        expected = u.path.parent.name if u.kind == "skill" else u.path.stem
        if u.name != expected:
            e(f"name '{u.name}' не совпадает с именем файла '{expected}'")
        if u.name in names:
            e(f"имя дублирует {names[u.name]}")
        names[u.name] = u.rel
        if not u.description:
            e("пустой description")
        if len(u.index_line) > DESC_MAX:
            e(f"строка для INDEX длиннее {DESC_MAX} символов ({len(u.index_line)}); укороти description или добавь index:")
        if u.kind == "lesson":
            if u.status not in STATUSES:
                e(f"status '{u.status}' не из {sorted(STATUSES)}")
            if not u.created or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", u.created):
                e("created должен быть датой YYYY-MM-DD")
            if not u.seen_in:
                e("seen_in пуст — откуда урок?")
            if not any(u.triggers.values()):
                e("нет ни одного триггера (triggers.keywords/commands/errors/paths)")
            if len(u.triggers["keywords"]) < 2:
                e("меньше двух keywords — хук почти никогда не покажет урок")
            n = u.prose_lines()
            if n > PROSE_MAX:
                e(f"тело {n} строк прозы при норме {PROSE_MAX} — разрежь на несколько единиц")
            if not u.body.lstrip().startswith("# "):
                e("тело начинается не с заголовка '# '")
            if "Урок" not in u.body and "## Правило" not in u.body:
                e("в теле нет блока «Урок» (что делать в следующий раз)")
            for pat in u.triggers["commands"] + u.triggers["errors"]:
                try:
                    re.compile(pat)
                except re.error as ex:
                    e(f"регулярка '{pat}' не компилируется: {ex}")
        elif u.kind == "stack":
            if len(u.triggers["keywords"]) < 2:
                e("у заметки по стеку меньше двух keywords")
    return errors


# --------------------------------------------------------------------------- index


def build_index(units: list[Unit] | None = None) -> str:
    units = units or load_units()
    lines = [
        "# INDEX — оглавление базы знаний",
        "",
        "Файл генерируется: `python3 tools/knowledge.py index`. Руками не править — правь шапку единицы.",
        "Формат: `- [путь] — описание (стек; from проекты)`. Статус кандидата помечен `[candidate]`.",
        "",
    ]
    order = {"skill": 0, "stack": 1, "lesson": 2}
    for kind, title in (("skill", "## Скиллы"), ("stack", "## Стеки"), ("lesson", "## Уроки")):
        group = [u for u in units if u.kind == kind and u.status != "archived"]
        if not group:
            continue
        lines.append(title)
        lines.append("")
        for u in sorted(group, key=lambda x: x.name):
            tag = " [candidate]" if u.status == "candidate" else ""
            src = f"; from {', '.join(u.seen_in)}" if u.seen_in else ""
            lines.append(f"- [{u.rel}]{tag} — {u.index_line} ({', '.join(u.stack)}{src})")
        lines.append("")
    archived = [u for u in units if u.status == "archived"]
    if archived:
        lines.append("## Архив (не импортируется, хуки не показывают)")
        lines.append("")
        for u in sorted(archived, key=lambda x: x.name):
            lines.append(f"- [{u.rel}] — {u.index_line}")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- match


def _kw_weight(kw: str) -> int:
    return 4 if (len(kw) >= 12 or re.search(r"[^\w\s]|\d", kw)) else 2


def match(prompt: str = "", command: str = "", files: list[str] | None = None, stack: list[str] | None = None,
          limit: int = 3, threshold: int = 3, exclude: set[str] | None = None, kinds=("lessons", "stacks"),
          use_keywords: bool = True) -> list[tuple[Unit, int, list[str]]]:
    files = files or []
    exclude = exclude or set()
    text = " ".join([prompt, command, " ".join(files)]).lower()
    usage = load_usage()
    scored = []
    for u in load_units(kinds):
        if u.status == "archived" or u.name in exclude:
            continue
        if stack and "any" not in u.stack and not set(s.lower() for s in u.stack) & set(s.lower() for s in stack):
            continue
        score, why = 0, []
        for kw in (u.triggers["keywords"] if use_keywords else []):
            if kw.lower() in text:
                w = _kw_weight(kw)
                score += w
                why.append(f"kw:{kw}")
        if command:
            for pat in u.triggers["commands"]:
                if re.search(pat, command):
                    score += 5
                    why.append(f"cmd:{pat}")
        for pat in u.triggers["errors"]:
            if re.search(pat, prompt + " " + command, flags=re.I):
                score += 5
                why.append(f"err:{pat}")
        for f in files:
            for pat in u.triggers["paths"]:
                if fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(Path(f).name, pat):
                    score += 3
                    why.append(f"path:{pat}")
                    break
        if score >= threshold:
            applied = usage.get(u.name, {}).get("applied", 0)
            scored.append((score, applied, u, why))
    scored.sort(key=lambda t: (-t[0], -t[1], t[2].name))
    return [(u, s, why) for s, _, u, why in scored[:limit]]


def render_hint(u: Unit, full: bool = True, max_lines: int = 40) -> str:
    body = u.body.strip()
    if not full:
        body = "\n".join(body.splitlines()[:max_lines])
    return f"[база знаний · {u.name}] {u.description}\n{body}\n"


# --------------------------------------------------------------------------- gc


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def gc_report(fetch: bool = True) -> str:
    units = load_units()
    lessons = [u for u in units if u.kind == "lesson"]
    usage = load_usage()
    out: list[str] = ["# Отчёт knowledge-gc", f"Дата: {dt.date.today().isoformat()}", ""]

    errs = lint(units)
    out.append(f"## Формат: {'ок' if not errs else f'{len(errs)} замечаний'}")
    out += [f"- {e}" for e in errs]
    out.append("")

    promote = [u for u in lessons if u.status == "candidate" and len(set(u.seen_in)) >= 2]
    out.append("## Кандидаты, замеченные в двух и более проектах → status: mature")
    out += [f"- {u.name} (seen_in: {', '.join(u.seen_in)})" for u in promote] or ["- нет"]
    out.append("")

    stale, silent = [], []
    for u in lessons:
        if u.status == "archived":
            continue
        age = u.age_days()
        rec = usage.get(u.name, {})
        if age is not None and age >= 90:
            if rec.get("shown", 0) >= 5 and rec.get("applied", 0) == 0:
                stale.append(f"- {u.name}: показан {rec.get('shown')} раз, применён 0 — триггер шумит или урок бесполезен")
            if rec.get("shown", 0) == 0 and rec.get("applied", 0) == 0:
                silent.append(f"- {u.name}: {age} дней, ни одного показа — триггеры не срабатывают, пересмотри keywords/commands")
    out.append("## Показывается, но не применяется (кандидаты в архив или на переформулировку)")
    out += stale or ["- нет"]
    out.append("")
    out.append("## Ни разу не показан за 90+ дней (триггеры мёртвые)")
    out += silent or ["- нет"]
    out.append("")

    dups = []
    for i, a in enumerate(lessons):
        ka = set(k.lower() for k in a.triggers["keywords"])
        for b in lessons[i + 1 :]:
            kb = set(k.lower() for k in b.triggers["keywords"])
            if not ka or not kb:
                continue
            inter = ka & kb
            j = len(inter) / len(ka | kb)
            if len(inter) >= 3 or j >= 0.4:
                dups.append(f"- {a.name} ↔ {b.name}: общие ключи {sorted(inter)} — слить или развести триггеры")
    out.append("## Похожие единицы (пересечение триггеров)")
    out += dups or ["- нет"]
    out.append("")

    big = [f"- {u.name}: {u.prose_lines()} строк" for u in lessons if u.prose_lines() > PROSE_MAX]
    out.append("## Слишком длинные (разрезать)")
    out += big or ["- нет"]
    out.append("")

    if fetch:
        git("fetch", "-q", "origin")
    behind = git("rev-list", "--count", "HEAD..origin/main")
    ahead = git("rev-list", "--count", "origin/main..HEAD")
    dirty = git("status", "--porcelain")
    out.append("## Синхронизация клона с origin")
    out.append(f"- отстаёт на {behind or '?'} коммитов, впереди на {ahead or '?'}; незакоммиченных файлов: {len(dirty.splitlines()) if dirty else 0}")
    out.append("")
    out.append(stats_text(units, usage))
    return "\n".join(out)


def stats_text(units: list[Unit] | None = None, usage: dict | None = None) -> str:
    units = units or load_units()
    usage = usage if usage is not None else load_usage()
    lessons = [u for u in units if u.kind == "lesson"]
    by_status: dict[str, int] = {}
    for u in lessons:
        by_status[u.status or "?"] = by_status.get(u.status or "?", 0) + 1
    shown = sum(r.get("shown", 0) for r in usage.values())
    applied = sum(r.get("applied", 0) for r in usage.values())
    top = sorted(usage.items(), key=lambda kv: -kv[1].get("applied", 0))[:5]
    lines = [
        "## Сводка",
        f"- уроков: {len(lessons)} ({', '.join(f'{k}: {v}' for k, v in sorted(by_status.items()))}); стеков: {sum(u.kind == 'stack' for u in units)}; скиллов: {sum(u.kind == 'skill' for u in units)}",
        f"- показов хуками всего: {shown}; применений: {applied}",
    ]
    if top and top[0][1].get("applied", 0):
        lines.append("- чаще всего применялись: " + ", ".join(f"{n} ({r.get('applied', 0)})" for n, r in top if r.get("applied", 0)))
    return "\n".join(lines)


# --------------------------------------------------------------------------- new


TEMPLATE = """---
name: {name}
description: {description}
stack: [{stack}]
status: candidate
created: {today}
seen_in: [{seen_in}]
triggers:
  keywords: [{keywords}]
  commands: []
  errors: []
  paths: []
---
# {title}

Контекст: <одна-две строки: где и при чём это всплыло, без имён проекта и путей>

Урок:
- <что делать в следующий раз — действие, а не рассуждение>
- <признак, по которому ситуацию узнать заранее>
"""


def new_unit(name: str, description: str, stack: list[str], seen_in: list[str], keywords: list[str], title: str | None) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise SystemExit("имя единицы — латиница, цифры и дефис (kebab-case)")
    path = KB / "lessons" / f"{name}.md"
    if path.exists():
        raise SystemExit(f"{path} уже существует — дописывай в него, а не создавай дубль")
    path.write_text(
        TEMPLATE.format(
            name=name,
            description=description,
            stack=", ".join(stack or ["any"]),
            today=dt.date.today().isoformat(),
            seen_in=", ".join(seen_in),
            keywords=", ".join(keywords),
            title=title or description,
        ),
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lint")
    p = sub.add_parser("index")
    p.add_argument("--check", action="store_true", help="не писать, а сравнить с текущим INDEX.md")
    p = sub.add_parser("match")
    p.add_argument("--prompt", default="")
    p.add_argument("--command", default="")
    p.add_argument("--files", default="")
    p.add_argument("--stack", default="")
    p.add_argument("--limit", type=int, default=3)
    p.add_argument("--threshold", type=int, default=3)
    p.add_argument("--exclude", default="")
    p.add_argument("--format", choices=("text", "json", "names"), default="text")
    p.add_argument("--brief", action="store_true", help="тело не длиннее 12 строк")
    p.add_argument("--no-keywords", action="store_true", help="только шаблоны команд/ошибок (режим хука команд)")
    p = sub.add_parser("hit")
    p.add_argument("name")
    p.add_argument("--project", default="")
    p = sub.add_parser("new")
    p.add_argument("name")
    p.add_argument("--description", required=True)
    p.add_argument("--stack", default="any")
    p.add_argument("--seen-in", default="")
    p.add_argument("--keywords", default="")
    p.add_argument("--title", default="")
    p = sub.add_parser("gc")
    p.add_argument("--no-fetch", action="store_true")
    sub.add_parser("stats")
    p = sub.add_parser("show")
    p.add_argument("name")
    a = ap.parse_args(argv)

    if a.cmd == "lint":
        errs = lint()
        for e in errs:
            print(e)
        print(f"{'ОК' if not errs else 'ОШИБКИ'}: {len(load_units())} единиц, {len(errs)} замечаний")
        return 1 if errs else 0
    if a.cmd == "index":
        text = build_index()
        idx = KB / "INDEX.md"
        if a.check:
            same = idx.exists() and idx.read_text(encoding="utf-8") == text
            print("INDEX.md актуален" if same else "INDEX.md устарел — запусти index")
            return 0 if same else 1
        idx.write_text(text, encoding="utf-8")
        print(f"INDEX.md пересобран: {text.count(chr(10))} строк")
        return 0
    if a.cmd == "match":
        res = match(
            prompt=a.prompt, command=a.command, files=[f for f in a.files.split(",") if f],
            stack=[s for s in a.stack.split(",") if s], limit=a.limit, threshold=a.threshold,
            exclude=set(x for x in a.exclude.split(",") if x), use_keywords=not a.no_keywords,
        )
        if a.format == "json":
            print(json.dumps([{"name": u.name, "score": s, "why": w, "path": u.rel} for u, s, w in res], ensure_ascii=False))
        elif a.format == "names":
            print("\n".join(u.name for u, _, _ in res))
        else:
            for u, s, w in res:
                print(render_hint(u, full=not a.brief, max_lines=12))
        return 0
    if a.cmd == "hit":
        if not find_unit(a.name):
            print(f"единицы '{a.name}' нет", file=sys.stderr)
            return 1
        record_usage([a.name], "applied", a.project or None)
        print(f"{a.name}: применение записано")
        return 0
    if a.cmd == "new":
        path = new_unit(
            a.name, a.description, [s.strip() for s in a.stack.split(",") if s.strip()],
            [s.strip() for s in a.seen_in.split(",") if s.strip()], [s.strip() for s in a.keywords.split(",") if s.strip()], a.title or None,
        )
        print(f"создан {path.relative_to(ROOT)} — заполни тело и триггеры, потом lint + index")
        return 0
    if a.cmd == "gc":
        print(gc_report(fetch=not a.no_fetch))
        return 0
    if a.cmd == "stats":
        print(stats_text())
        return 0
    if a.cmd == "show":
        u = find_unit(a.name)
        if not u:
            print(f"единицы '{a.name}' нет", file=sys.stderr)
            return 1
        print(u.path.read_text(encoding="utf-8"))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
