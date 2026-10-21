#!/usr/bin/env python3
"""Евалы системы самообучения.

Офлайн (бесплатно, по умолчанию): для каждого кейса из evals/cases.json проверяем, что
нужный урок попадает в топ-3 подбора по промту/команде — это регрессионный тест триггеров.
Кейс с ключом "tier" проверяет распознавание уровня задачи в промте хуком (hook.detect_tier):
"tier": "simple|medium|complex" или null, когда уровень не назван.
Кейс с ключом "resolve" проверяет решение хука по промту и записи сессии "saved" (hook.resolve_tier):
{"tier", "source", "line"} — что запишется (null — ничего) и регулярка по строке агенту; уровень не назван —
«простая» по умолчанию, а названный ранее или выбранный кнопками умолчанием не перезаписывается.
Кейс с ключом "kinds" (например ["improvements"]) ищет в этих разделах базы — так проверяются триггеры улучшений,
по которым simplify-review и improve-sweep подбирают их под задачу.
Кейс с ключом "cwd" проверяет, какую папку хук считает проектом (hook.project_of): "project" — ожидаемое имя,
"" — не проект (временная папка, рабочая копия в scratchpad); "<repo>" в cwd — корень этого репозитория.

--live (платно, вручную): прогоняем `claude -p` во временном проекте с подключёнными
хуками и проверяем, что ответ содержит ожидаемый признак (expect — регулярка).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hook  # noqa: E402
import knowledge as kb  # noqa: E402

CASES = kb.ROOT / "evals" / "cases.json"


def offline(cases: list[dict]) -> int:
    failed = 0
    for c in cases:
        if "resolve" in c:
            exp = c["resolve"]
            tier, source, line = hook.resolve_tier(c.get("prompt", ""), c.get("saved") or {})
            ok = (tier, source) == (exp.get("tier"), exp.get("source")) and re.search(exp.get("line", ""), line) is not None
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} resolve={str(exp.get('tier')):<8} got={str(tier):<8} src={str(source):<8} «{c.get('prompt', '')[:50]}»")
            continue
        if "cwd" in c:
            got = hook.project_of(c["cwd"].replace("<repo>", str(kb.ROOT)))[1]
            ok = got == c["project"]
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} project={c['project']!r:<16} got={got!r:<16} «{c['cwd'][:50]}»")
            continue
        if "tier" in c:
            got = hook.detect_tier(c.get("prompt", ""))
            ok = got == c["tier"]
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} tier={str(c['tier']):<8} got={str(got):<8} «{c.get('prompt', '')[:60]}»")
            continue
        res = kb.match(prompt=c.get("prompt", ""), command=c.get("command", ""), files=c.get("files", []),
                       stack=c.get("stack"), limit=3, threshold=3 if c.get("prompt") else 4,
                       use_keywords=bool(c.get("prompt")), kinds=tuple(c.get("kinds") or ("lessons", "stacks")))
        names = [u.name for u, _, _ in res]
        ok = c["unit"] in names
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {c['unit']:<40} top3={names}")
    print(f"\nофлайн: {len(cases) - failed}/{len(cases)} кейсов прошли")
    return 1 if failed else 0


def live(cases: list[dict], model: str | None) -> int:
    failed = 0
    for c in [c for c in cases if c.get("expect")]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "knowledge.json").write_text(json.dumps({"stack": c.get("stack") or ["any"]}), encoding="utf-8")
            (root / "CLAUDE.md").write_text("Отвечай кратко, по-русски. Ничего не выполняй, только опиши план действий.\n", encoding="utf-8")
            cmd = ["claude", "-p", c.get("prompt") or c.get("command", ""), "--output-format", "text"]
            if model:
                cmd += ["--model", model]
            try:
                out = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=300).stdout
            except (subprocess.SubprocessError, OSError) as ex:
                out = f"<error: {ex}>"
            ok = re.search(c["expect"], out, flags=re.I | re.S) is not None
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {c['unit']:<40} expect=/{c['expect']}/")
            if not ok:
                print("     ответ: " + " ".join(out.split())[:300])
    print(f"\nlive: {sum(1 for c in cases if c.get('expect')) - failed} прошли, {failed} упали")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--model", default=None)
    a = ap.parse_args()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    rc = offline(cases)
    if a.live:
        rc = live(cases, a.model) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
