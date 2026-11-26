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
Кейс с ключом "below" проверяет шкалу нейронок (hook.model_below): "model" слабее минимума проекта "min" — true,
не слабее — false, минимума нет или нейронка неизвестна — null.
Кейс с ключом "understood" проверяет, понял ли хук запись минимума "min" (hook.min_model_understood): семейство из
шкалы или «любая» — true; опечатка или описание словами — false (о такой записи хук говорит на старте сессии).
Кейс с ключом "gate" прогоняет запрет инструментов для нейронки слабее минимума (hook.gate_reason) во временном
проекте: "min" — min_model проекта, "models" — записи журнала сессии по порядку (строка — ответ нейронки,
[модель, true] — ответ субагента, {"request": модель} — запрос к модели: он в журнале раньше первого ответа),
"confirmed" — уже нажатое «Продолжить», "answer" — ответ на вопрос «Нейронка», "prompt" — новый промт перед вызовом,
"tool" — инструмент, "agent" — вызов из субагента; "deny" — ждём запрет (true) или пропуск (false).
Кейс с ключом "ask" проверяет, что хук говорит агенту после ответов владельца кнопками (hook.on_ask) в таком же
временном проекте: "asked" — список [заголовок, вопрос, ответ], "says" — регулярка по выводу хука ("^$" — молчит).

--live (платно, вручную): прогоняем `claude -p` во временном проекте с подключёнными
хуками и проверяем, что ответ содержит ожидаемый признак (expect — регулярка).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hook  # noqa: E402
import knowledge as kb  # noqa: E402

CASES = kb.ROOT / "evals" / "cases.json"


def _journal_record(item) -> dict:
    if isinstance(item, dict):  # запрос к модели; "agentId" — запрос субагента
        return {"type": "api-request", "params": {"model": item["request"]}, **{k: v for k, v in item.items() if k != "request"}}
    model, side = item if isinstance(item, list) else (item, False)
    return {"type": "assistant", "isSidechain": side, "message": {"model": model}}


@contextlib.contextmanager
def gate_project(g: dict):
    """Вход хука для временного проекта: min_model, журнал сессии с записями нейронок; записи хука — во временной папке."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".claude").mkdir()
        (root / ".claude" / "knowledge.json").write_text(json.dumps({"min_model": g.get("min", "")}), encoding="utf-8")
        inp = {"session_id": "eval", "cwd": tmp, "tool_name": g.get("tool", "Edit")}
        if "models" in g:
            inp["transcript_path"] = str(root / "session.jsonl")
            Path(inp["transcript_path"]).write_text(
                "".join(json.dumps(_journal_record(m)) + "\n" for m in g["models"]), encoding="utf-8")
        if g.get("agent"):
            inp["agent_id"] = "eval-agent"
        with (mock.patch.object(hook, "GATE_DIR", root / "gate"), mock.patch.object(hook, "TIER_DIR", root / "tier"),
              mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmp})):
            if g.get("confirmed"):
                hook.save_gate("eval", {"confirmed": g["confirmed"]})
            yield inp


def gate_denies(g: dict) -> bool:
    """Запретил ли хук инструмент (hook.gate_reason) после ответа на вопрос «Нейронка» и нового промта, если заданы."""
    with gate_project(g) as inp:
        if "answer" in g:
            hook.gate_on_answer(inp, g["answer"])
        if "prompt" in g:
            hook.gate_on_prompt(inp, g["prompt"])
        return bool(hook.gate_reason(inp))


def ask_says(g: dict) -> str:
    """Что хук говорит агенту после ответов владельца кнопками (hook.on_ask): "asked" — [заголовок, вопрос, ответ]."""
    with gate_project(g) as inp, contextlib.redirect_stdout(io.StringIO()) as out:
        hook.on_ask({**inp, "tool_name": "AskUserQuestion",
                     "tool_input": {"questions": [{"header": h, "question": q} for h, q, _ in g["asked"]]},
                     "tool_response": {"answers": {q: a for _, q, a in g["asked"]}}})
    return out.getvalue()


def offline(cases: list[dict]) -> int:
    failed = 0
    for c in cases:
        if "below" in c:
            got = hook.model_below(c.get("model", ""), c.get("min", ""))
            ok = got is c["below"]
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} below={str(c['below']):<6} got={str(got):<6} «{c.get('model', '')}» при минимуме «{c.get('min', '')}»")
            continue
        if "understood" in c:
            got = hook.min_model_understood(c["min"])
            ok = got is c["understood"]
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} understood={str(c['understood']):<6} got={str(got):<6} минимум «{c['min']}»")
            continue
        if "gate" in c:
            got = gate_denies(c["gate"])
            ok = got is c["deny"]
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} deny={str(c['deny']):<6} got={str(got):<6} {json.dumps(c['gate'], ensure_ascii=False)[:90]}")
            continue
        if "ask" in c:
            got = ask_says(c["ask"])
            ok = re.search(c["says"], got) is not None
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} ask says=/{c['says']}/ {json.dumps(c['ask']['asked'], ensure_ascii=False)[:80]}")
            continue
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
