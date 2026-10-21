#!/usr/bin/env python3
"""Инструмент базы знаний claude-start. Только стандартная библиотека.

Команды:
  lint                  проверить формат всех единиц знания
  index                 пересобрать knowledge/INDEX.md из шапок файлов
  match                 подобрать единицы под промт / команду / файлы (для хуков)
  hit <name>            отметить, что урок реально применён (счётчик в usage.json)
  new <name> ...        создать каркас новой единицы в правильном формате (--improvement — улучшение)
  improvements          подобрать улучшения из базы под проект: по стеку и задаче, без решённых в нём, по рейтингу
  vote <name> ...       записать ответ владельца на улучшение (принято / отклонено / отложено / не применимо) и оценку
  gc                    отчёт для уборки: дубли, протухшее, кандидаты на зрелость
  stats                 сводка по базе
  show <name>           напечатать единицу
"""
from __future__ import annotations

import argparse
import datetime as dt
from collections import namedtuple
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
INDEX = KB / "INDEX.md"
KINDS = {"lessons": "lesson", "stacks": "stack", "skills": "skill", "improvements": "improvement"}
STATUSES = {"candidate", "mature", "archived"}
LIFECYCLE = ("lesson", "improvement")  # единицы с жизненным циклом: статус, дата, проекты, обязательные триггеры
MATURE_PROJECTS = 2  # зрелость — замечено (урок) или принято (улучшение) в стольких проектах
REQUIRED_BLOCKS = {"lesson": (("Урок", "## Правило"),), "improvement": (("Когда",), ("Предложение",))}  # варианты через «или»
IMPROVEMENT_KINDS = {"solution", "module", "code"}  # что улучшает: решение задачи, модуль, где шла работа, код
VOTES = ("accepted", "rejected", "deferred", "na")  # ответ владельца: принято / отклонено / отложено / не применимо
VOTE_RU = {"accepted": "принято", "rejected": "отклонено", "deferred": "отложено", "na": "не применимо"}
RETRY_DAYS = {"deferred": 30, "na": 180}  # отложенное предлагается снова через месяц, «не применимо» перепроверяется через полгода
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
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


def _front_end(text: str) -> int:
    """Где кончается шапка (---…---); -1 — шапки нет."""
    return text.find("\n---", 3) if text.startswith("---") else -1


def _days_since(iso: str, today: dt.date | None = None) -> int | None:
    try:
        return ((today or dt.date.today()) - dt.date.fromisoformat(iso)).days
    except ValueError:
        return None


def _maturity(projects: list[str]) -> str:
    return "mature" if len(set(projects)) >= MATURE_PROJECTS else "candidate"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    end = _front_end(text)
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
        self.status = str(self.meta.get("status") or ("" if self.kind in LIFECYCLE else "mature"))
        self.seen_in = _as_list(self.meta.get("seen_in"))
        self.created = str(self.meta.get("created") or "")
        self.scope = str(self.meta.get("scope") or "project")
        trig = self.meta.get("triggers") or {}
        self.triggers = {k: _as_list(trig.get(k)) for k in TRIGGER_KEYS} if isinstance(trig, dict) else {k: [] for k in TRIGGER_KEYS}
        self.ikind = str(self.meta.get("kind") or "")  # улучшение: solution | module | code
        self.benefit = _as_number(self.meta.get("benefit"))  # улучшение: оценка выгоды агентом 1–5
        self.rating = _as_number(self.meta.get("rating"))  # улучшение: оценка владельца 1–5, None — не оценивал
        self.revised = str(self.meta.get("revised") or "")  # улучшение: дата переформулировки — ответы старше неё не считаются

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
        return _days_since(self.created, today) if self.created else None


def _as_number(v) -> float | None:
    if v is None or v == "" or isinstance(v, (dict, list)):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _fmt_num(v: float | None) -> str:
    if v is None:
        return "—"
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def _as_list(v) -> list[str]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def load_units(kinds=("lessons", "stacks", "skills", "improvements")) -> list[Unit]:
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
        if u.kind in LIFECYCLE:
            if u.status not in STATUSES:
                e(f"status '{u.status}' не из {sorted(STATUSES)}")
            if not u.created or not _DATE_RE.fullmatch(u.created):
                e("created должен быть датой YYYY-MM-DD")
            if not u.seen_in and not u.revised:
                e("seen_in пуст — в каком проекте это появилось?")
            if not any(u.triggers.values()):
                e("нет ни одного триггера (triggers.keywords/commands/errors/paths)")
            if len(u.triggers["keywords"]) < 2:
                e("меньше двух keywords — триггеры почти никогда не найдут единицу")
            n = u.prose_lines()
            if n > PROSE_MAX:
                e(f"тело {n} строк прозы при норме {PROSE_MAX} — разрежь на несколько единиц")
            if not u.body.lstrip().startswith("# "):
                e("тело начинается не с заголовка '# '")
            for alternatives in REQUIRED_BLOCKS[u.kind]:
                if not any(a in u.body for a in alternatives):
                    e(f"в теле нет блока «{alternatives[0]}»")
            if u.kind == "improvement":
                if u.ikind not in IMPROVEMENT_KINDS:
                    e(f"kind '{u.ikind}' не из {sorted(IMPROVEMENT_KINDS)} — что улучшает: решение, модуль или код")
                if u.benefit is None or not (1 <= u.benefit <= 5):
                    e("benefit — оценка выгоды агентом, от 1 до 5")
                if u.rating is not None and not (1 <= u.rating <= 5):
                    e("rating — оценка владельца от 1 до 5 (пусто — ещё не оценивал)")
                if u.revised and not _DATE_RE.fullmatch(u.revised):
                    e("revised — дата переформулировки YYYY-MM-DD")
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
        "Улучшение: `(что улучшает; стек; агент — оценка выгоды, владелец — его оценка; from проекты)`.",
        "",
    ]
    for kind, title in (("skill", "## Скиллы"), ("stack", "## Стеки"), ("improvement", "## Улучшения"), ("lesson", "## Уроки")):
        group = [u for u in units if u.kind == kind and u.status != "archived"]
        if not group:
            continue
        lines.append(title)
        lines.append("")
        for u in sorted(group, key=lambda x: x.name):
            tag = " [candidate]" if u.status == "candidate" else ""
            src = f"; from {', '.join(u.seen_in)}" if u.seen_in else ""
            what = f"{u.ikind}; " if u.kind == "improvement" else ""
            score = f"; агент {_fmt_num(u.benefit)}, владелец {_fmt_num(u.rating)}" if u.kind == "improvement" else ""
            lines.append(f"- [{u.rel}]{tag} — {u.index_line} ({what}{', '.join(u.stack)}{score}{src})")
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


def _stack_ok(u: Unit, stack: list[str] | None) -> bool:
    return not stack or "any" in u.stack or bool(set(s.lower() for s in u.stack) & set(s.lower() for s in stack))


Query = namedtuple("Query", "prompt command files text")  # text — склейка в нижнем регистре, считается один раз на подбор


def _query(prompt: str = "", command: str = "", files: list[str] | None = None) -> Query:
    files = files or []
    return Query(prompt, command, files, " ".join([prompt, command, " ".join(files)]).lower())


def _trigger_score(u: Unit, q: Query, use_keywords: bool = True) -> tuple[int, list[str]]:
    """Сколько триггеров единицы совпало с запросом — и какие именно."""
    score, why = 0, []
    for kw in (u.triggers["keywords"] if use_keywords else []):
        if kw.lower() in q.text:
            score += _kw_weight(kw)
            why.append(f"kw:{kw}")
    if q.command:
        for pat in u.triggers["commands"]:
            if re.search(pat, q.command):
                score += 5
                why.append(f"cmd:{pat}")
    for pat in u.triggers["errors"]:
        if re.search(pat, q.prompt + " " + q.command, flags=re.I):
            score += 5
            why.append(f"err:{pat}")
    for f in q.files:
        for pat in u.triggers["paths"]:
            if fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(Path(f).name, pat):
                score += 3
                why.append(f"path:{pat}")
                break
    return score, why


def match(prompt: str = "", command: str = "", files: list[str] | None = None, stack: list[str] | None = None,
          limit: int = 3, threshold: int = 3, exclude: set[str] | None = None, kinds=("lessons", "stacks"),
          use_keywords: bool = True) -> list[tuple[Unit, int, list[str]]]:
    exclude = exclude or set()
    usage = load_usage()
    q = _query(prompt, command, files)
    scored = []
    for u in load_units(kinds):
        if u.status == "archived" or u.name in exclude or not _stack_ok(u, stack):
            continue
        score, why = _trigger_score(u, q, use_keywords)
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


# --------------------------------------------------------------------------- improvements


def _live(rec: dict, revised: str = "") -> dict:
    """Ответы проектов, которые ещё в силе: после переформулировки единицы (revised) прежние ответы не считаются."""
    return {p: d for p, d in (rec.get("decisions") or {}).items() if not revised or str(d.get("date", "")) >= revised}


def _voted(rec: dict, answer: str, revised: str = "") -> list[str]:
    """Проекты, ответившие так; единственный источник счётчиков — история decisions."""
    return [p for p, d in _live(rec, revised).items() if d.get("answer") == answer]


def _rating(rec: dict, revised: str = "") -> float | None:
    """Средняя оценка владельца по проектам, где улучшение принято и ответ в силе."""
    accepted = _voted(rec, "accepted", revised)
    scores = [float(s) for p, s in (rec.get("scores") or {}).items() if p in accepted]
    return round(sum(scores) / len(scores), 1) if scores else None


def decided_in(rec: dict, project: str, revised: str = "") -> str | None:
    """Ответ проекта, пока он в силе: отложенное и «не применимо» со временем предлагаются снова."""
    d = _live(rec, revised).get(project) or {}
    answer = d.get("answer")
    if answer in RETRY_DAYS:
        age = _days_since(str(d.get("date", "")))
        if age is None or age >= RETRY_DAYS[answer]:
            return None
    return answer


def improvements(project: str = "", stack: list[str] | None = None, prompt: str = "", files: list[str] | None = None,
                 include_all: bool = False) -> list[dict]:
    """Улучшения под проект: по стеку, без решённых в нём; сперва совпавшие с задачей, затем по оценке владельца,
    балансу принято/отклонено и оценке агента."""
    usage = load_usage()
    q = _query(prompt, "", files)
    rows = []
    for u in load_units(("improvements",)):
        if u.status == "archived" or not _stack_ok(u, stack):
            continue
        rec = usage.get(u.name, {})
        decided = decided_in(rec, project, u.revised) if project else None
        if decided and not include_all:
            continue
        score, why = _trigger_score(u, q)
        rows.append({
            "unit": u, "score": score, "why": why, "decided": decided, "rating": _rating(rec, u.revised),
            "accepted": len(_voted(rec, "accepted", u.revised)), "rejected": len(_voted(rec, "rejected", u.revised)),
        })
    unrated = 2.5  # ещё не оценённое идёт после оценённого на 3 и выше, но раньше оценённого на 2 и ниже
    rows.sort(key=lambda r: (-r["score"], -(r["rating"] if r["rating"] is not None else unrated),
                             -(r["accepted"] - r["rejected"]), -(r["unit"].benefit or 0), r["unit"].name))
    return rows


def render_improvement(r: dict, full: bool = False) -> str:
    u = r["unit"]
    head = (
        f"[улучшение · {u.name}] {u.description}\n"
        f"  {u.ikind}; {', '.join(u.stack)}; владелец {_fmt_num(r['rating'])}, агент {_fmt_num(u.benefit)}; "
        f"принято {r['accepted']}, отклонено {r['rejected']}; from {', '.join(u.seen_in) or '—'}"
        + (f"; совпало: {', '.join(r['why'])}" if r["why"] else "")
        + (f"; в этом проекте: {r['decided']}" if r["decided"] else "")
    )
    return head + ("\n" + u.body.strip() + "\n" if full else "")


def _set_front(text: str, key: str, value: str) -> str:
    """Заменить строку `key: …` в шапке единицы вместе с блочным списком под ней; нет такой — вставить перед triggers:."""
    end = _front_end(text)
    if end < 0:
        raise SystemExit("у единицы нет шапки (frontmatter) — сначала приведи её к формату, см. lint")
    head, rest = text[:end], text[end:]
    line = f"{key}: {value}".rstrip()
    pat = rf"^{key}:[^\n]*(?:\n[ \t]*-[^\n]*)*"
    if re.search(pat, head, flags=re.M):
        head = re.sub(pat, lambda _: line, head, count=1, flags=re.M)
    elif re.search(r"^triggers:", head, flags=re.M):
        head = re.sub(r"^triggers:", lambda _: f"{line}\ntriggers:", head, count=1, flags=re.M)
    else:
        head += f"\n{line}"
    return head + rest


def _record_decision(data: dict, name: str, project: str, answer: str, score: float | None = None, reason: str = "") -> dict:
    """Ответ проекта в usage.json: последний ответ проекта, его причина и оценка; отказ снимает оценку."""
    rec = data.setdefault(name, {})
    decision = {"answer": answer, "date": dt.date.today().isoformat()}
    if reason:
        decision["reason"] = reason
    rec.setdefault("decisions", {})[project] = decision
    scores = rec.setdefault("scores", {})
    if score is not None:
        scores[project] = score
    elif answer != "accepted":
        scores.pop(project, None)  # оценка ставится сделанному; отказ её снимает
    return rec


def _sync_unit(u: Unit, rec: dict) -> Unit:
    """Шапка улучшения — производная от истории ответов: seen_in — принявшие проекты, status — зрелость по ним
    (архив не трогается), rating — средняя оценка владельца. Переписывает файл, возвращает перечитанную единицу."""
    accepted = _voted(rec, "accepted", u.revised)
    text = u.path.read_text(encoding="utf-8")
    text = _set_front(text, "seen_in", f"[{', '.join(accepted)}]")
    if u.status != "archived":
        text = _set_front(text, "status", _maturity(accepted))
    rating = _rating(rec, u.revised)
    text = _set_front(text, "rating", _fmt_num(rating) if rating is not None else "")
    u.path.write_text(text, encoding="utf-8")
    return Unit(u.path)


def vote(name: str, project: str, answer: str, score: float | None = None, reason: str = "", memory: str = "") -> str:
    """Ответ владельца на улучшение: история в usage.json, шапка единицы и INDEX.md — следом; memory — путь к
    simplify-memory.md проекта, туда дописывается строка ответа (один шаг вместо двух, решение владельца 21.10.2026)."""
    if score is not None and not (1 <= score <= 5):
        raise SystemExit("оценка владельца — от 1 до 5")
    if score is not None and answer != "accepted":
        raise SystemExit("оценка ставится только сделанному улучшению (--answer accepted)")
    if not project:
        raise SystemExit("--project обязателен: решения и зрелость считаются по проектам")
    u = find_unit(name)
    if not u or u.kind != "improvement":
        raise SystemExit(f"улучшения '{name}' нет (knowledge/improvements/{name}.md)")
    data = load_usage()
    rec = _record_decision(data, name, project, answer, score, reason)
    save_usage(data)
    u = _sync_unit(u, rec)
    INDEX.write_text(build_index(), encoding="utf-8")
    if memory:
        with open(memory, "a", encoding="utf-8") as fh:
            fh.write(f"| {dt.date.today().isoformat()} | улучшение из базы {name}: {u.description} | {VOTE_RU[answer]} | {reason} |\n")
    return (f"{name}: {project} — {answer}" + (f", оценка {_fmt_num(score)}" if score is not None else "")
            + f"; принято в {len(_voted(rec, 'accepted', u.revised))} проект(ах), status: {u.status}, rating: {_fmt_num(u.rating)}")


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

    promote = [u for u in units if u.kind in LIFECYCLE and u.status == "candidate" and _maturity(u.seen_in) == "mature"]
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

    rows = []
    for u in units:
        if u.kind != "improvement" or u.status == "archived":
            continue
        rec = usage.get(u.name, {})
        acc, rej = len(_voted(rec, "accepted", u.revised)), len(_voted(rec, "rejected", u.revised))
        rating = _rating(rec, u.revised)
        if rej >= 2 and acc == 0:
            rows.append(f"- {u.name}: отклонено в {rej} проектах, не принято нигде — в архив или переформулировать")
        if rating is not None and rating <= 2:
            rows.append(f"- {u.name}: оценка владельца {_fmt_num(rating)} — переформулировать или в архив")
        if len(_live(rec, u.revised)) >= 3 and acc == 0 and rej == 0:
            rows.append(f"- {u.name}: {len(dec)} раз отложено или не применимо, не принято нигде — сузь триггеры или в архив")
    out.append("## Улучшения: продвинуть или убрать")
    out += rows or ["- нет"]
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
    imps = [u for u in units if u.kind == "improvement"]
    if imps:
        acc = sum(len(_voted(usage.get(u.name, {}), "accepted", u.revised)) for u in imps)
        rej = sum(len(_voted(usage.get(u.name, {}), "rejected", u.revised)) for u in imps)
        rated = [r for r in (_rating(usage.get(u.name, {}), u.revised) for u in imps) if r is not None]
        lines.append(
            f"- улучшений: {len(imps)} ({sum(u.status == 'mature' for u in imps)} зрелых); голосов: принято {acc}, отклонено {rej}"
            + (f"; средняя оценка владельца {sum(rated) / len(rated):.1f}" if rated else "")
        )
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


IMPROVEMENT_TEMPLATE = """---
name: {name}
description: {description}
kind: {kind}
stack: [{stack}]
status: {status}
created: {today}
seen_in: [{seen_in}]
benefit: {benefit}
rating:
triggers:
  keywords: [{keywords}]
  commands: []
  errors: []
  paths: []
---
# {title}

Когда: <признак, по которому улучшение применимо, — одна-две строки, без имён проекта и путей>

Предложение: <вопрос владельцу его словами: что изменить, что он получит, цена — «… Делаем?»>

Выгода: <что получит владелец или пользователь>. Цена: <~строк / файлов / минут>.
"""


def new_unit(name: str, description: str, stack: list[str], seen_in: list[str], keywords: list[str], title: str | None,
             improvement: bool = False, kind: str = "", benefit: int = 0) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise SystemExit("имя единицы — латиница, цифры и дефис (kebab-case)")
    fields = dict(
        name=name, description=description, stack=", ".join(stack or ["any"]), today=dt.date.today().isoformat(),
        seen_in=", ".join(seen_in), keywords=", ".join(keywords), title=title or description,
    )
    if improvement:
        if kind not in IMPROVEMENT_KINDS:
            raise SystemExit(f"--kind — один из: {', '.join(sorted(IMPROVEMENT_KINDS))} (решение, модуль, код)")
        if not 1 <= benefit <= 5:
            raise SystemExit("--benefit — оценка выгоды агентом, от 1 до 5")
        path = KB / "improvements" / f"{name}.md"
        text = IMPROVEMENT_TEMPLATE.format(kind=kind, benefit=benefit, status=_maturity(seen_in), **fields)
    else:
        path = KB / "lessons" / f"{name}.md"
        text = TEMPLATE.format(**fields)
    if path.exists():
        raise SystemExit(f"{path} уже существует — дописывай в него, а не создавай дубль")
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if improvement and seen_in:  # проект-источник уже принял улучшение — это его первый голос
        data = load_usage()
        for proj in seen_in:
            _record_decision(data, name, proj, "accepted")
        save_usage(data)
    return path


# --------------------------------------------------------------------------- cli


def _csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


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
    p.add_argument("--improvement", action="store_true", help="улучшение (knowledge/improvements/), а не урок")
    p.add_argument("--kind", default="", help="улучшение: solution | module | code")
    p.add_argument("--benefit", type=int, default=0, help="улучшение: оценка выгоды агентом 1–5")
    p = sub.add_parser("improvements")
    p.add_argument("--project", default="", help="без решённых в этом проекте (отложенное — снова через 30 дней, «не применимо» — через полгода)")
    p.add_argument("--stack", default="")
    p.add_argument("--prompt", default="", help="цель задачи — совпавшие по триггерам идут первыми")
    p.add_argument("--files", default="", help="изменённые файлы через запятую")
    p.add_argument("--all", action="store_true", help="показать и решённые в проекте, с их ответом")
    p.add_argument("--full", action="store_true", help="с телом единицы (блоки «Когда», «Предложение», «Выгода»)")
    p = sub.add_parser("vote")
    p.add_argument("name")
    p.add_argument("--project", required=True)
    p.add_argument("--answer", required=True, choices=VOTES)
    p.add_argument("--score", type=float, default=None, help="оценка владельца 1–5 после того, как он увидел результат")
    p.add_argument("--reason", default="", help="причина, если владелец назвал: в историю и в память проекта")
    p.add_argument("--memory", default="", help="путь к .claude/simplify-memory.md проекта — строка ответа допишется сама")
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
        if a.check:
            same = INDEX.exists() and INDEX.read_text(encoding="utf-8") == text
            print("INDEX.md актуален" if same else "INDEX.md устарел — запусти index")
            return 0 if same else 1
        INDEX.write_text(text, encoding="utf-8")
        print(f"INDEX.md пересобран: {text.count(chr(10))} строк")
        return 0
    if a.cmd == "match":
        res = match(
            prompt=a.prompt, command=a.command, files=_csv(a.files), stack=_csv(a.stack), limit=a.limit,
            threshold=a.threshold, exclude=set(_csv(a.exclude)), use_keywords=not a.no_keywords,
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
        if (a.kind or a.benefit) and not a.improvement:
            raise SystemExit("--kind и --benefit — только вместе с --improvement")
        path = new_unit(
            a.name, a.description, _csv(a.stack), _csv(a.seen_in), _csv(a.keywords), a.title or None,
            improvement=a.improvement, kind=a.kind, benefit=a.benefit,
        )
        print(f"создан {path.relative_to(ROOT)} — заполни тело и триггеры, потом lint + index")
        return 0
    if a.cmd == "improvements":
        rows = improvements(project=a.project, stack=_csv(a.stack), prompt=a.prompt, files=_csv(a.files), include_all=a.all)
        if not rows:
            print("в базе нет улучшений под этот проект" + (" (решённые скрыты: --all)" if a.project else ""))
        for r in rows:
            print(render_improvement(r, full=a.full))
        return 0
    if a.cmd == "vote":
        print(vote(a.name, a.project, a.answer, a.score, a.reason, a.memory))
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
