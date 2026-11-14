#!/usr/bin/env node
// Программа техзаданий (навык spec-write): папка ТЗ, очередь прохода по пунктам, проверка строения и готовности
// к запуску. Node 20+, без пакетов. Порядок работы — SKILL.md рядом.
//
//   node tz.js new <имя> [--root <проект>] [--small]     создать technical-docs/<имя>/ с ТЗ и протоколом
//   node tz.js check <ТЗ> [--launch] [--root <проект>]   строение; --launch — можно ли запускать
//   node tz.js next <ТЗ>                                  следующий пункт на проход
//   node tz.js stamp <ТЗ> <П7> <итог> [--touch П4,П11]    отметить; --touch — вернуть задетые в очередь
//   node tz.js status <ТЗ>                                счёт одной строкой
//   node tz.js index [--root <проект>]                    пересобрать оглавление technical-docs/README.md
//
// Что значат итоги (чисто · исправлен · вопрос · показ) — SKILL.md, раздел 3.
"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const DOCS = "technical-docs";
const VERDICTS = ["чисто", "исправлен", "вопрос", "показ"];
const VERDICT_ALIAS = { "уточнён": "исправлен", "уточнен": "исправлен" };
const SOURCES = ["владелец", "решение", "допущение", "защита", "правило"];
const SOURCE_RE = new RegExp(`\\[(${SOURCES.join("|")})[^\\]]*\\]`, "i");
const SOURCE_STRIP = new RegExp(`[*_]*\\[(?:${SOURCES.join("|")})[^\\]]*\\][*_]*`, "gi");
// Пункт: «**П7.** текст» — допустимы маркер списка, цитата, «**П7:**», «**П7**.», «**П7. Заголовок.** текст».
// «**П5–П7**» — ссылка на диапазон, не пункт.
const LEAD = "^\\s*(?:>\\s*)?(?:(?:[-*+]|\\d+[.)])\\s+)?";
const NOT_ID_TAIL = "(?![\\dA-Za-zА-Яа-яЁё–—-])";
const ITEM_RE = new RegExp(`${LEAD}\\*\\*(П\\d+)${NOT_ID_TAIL}[.:]?\\s*(.*)$`);
const ITEM_LIKE = new RegExp(`${LEAD}[*_]{0,2}П\\d+${NOT_ID_TAIL}`);
const HEAD_RE = /^(#{1,6})\s+(.*?)\s*$/;
const REQUIRED = [
  ["Зачем", /зачем/i],
  ["Что вы увидите, когда готово", /увидите|сценарий/i],
  ["Чего не делаем", /не делаем/i],
  ["Как этим пользуются", /пользу/i],
  ["Пункты задания", /пункты/i],
  ["Этапы и точки проверки", /этап/i],
  ["Решения владельца", /решения/i],
  ["Открытые вопросы", /открытые вопросы/i],
];
const READERS = [["Читатель 1", /читатель\s*1/i], ["Читатель 2", /читатель\s*2/i], ["Рецензент простоты", /рецензент простоты/i]];
const PROTOCOL_HEADS = [...READERS.map(r => r[1]), /находки/i, /вопросы и ответы/i, /правки на точках/i];
// Слова, по которым нельзя сказать «сделано / не сделано». Только замечание: слово бывает и к месту.
const VAGUE = new RegExp("(?<![а-яё])(" + [
  "удобн[а-яё]*", "быстро", "быстр(?:ый|ая|ое|ые)", "красив[а-яё]*", "интуитивн[а-яё]*", "современн[а-яё]*",
  "гибк[а-яё]*", "оптимальн[а-яё]*", "нормальн[а-яё]*", "корректн[а-яё]*", "при необходимости", "по возможности",
  "и т\\. ?[дп]\\.", "и так далее", "и прочее", "например", "желательно", "как-нибудь", "несколько", "достаточно",
].join("|") + ")(?![а-яё])", "gi");
const LIMIT_ITEMS = 40, LIMIT_STAGES = 7, LIMIT_SMALL = 14;
const INDEX_START = "<!-- tz-index:start -->", INDEX_END = "<!-- tz-index:end -->";

function fail(msg) { console.error(msg); process.exit(1); }

// Заборы кода и комментарии разметки пунктами и разделами не считаются; номера строк сохраняются.
// Забор закрывается тем же знаком и не короче открывающего: ~~~ внутри ``` — обычный текст.
function visibleLines(text) {
  const lines = String(text).replace(/^﻿/, "").replace(/\r\n?/g, "\n")
    .replace(/<!--[\s\S]*?-->/g, m => m.replace(/[^\n]/g, "")).split("\n");
  let fence = null;
  return lines.map(l => {
    const m = l.match(/^\s*(`{3,}|~{3,})(.*)$/);
    if (fence) {
      if (m && m[1][0] === fence.ch && m[1].length >= fence.len && !m[2].trim()) fence = null;
      return "";
    }
    if (m) { fence = { ch: m[1][0], len: m[1].length }; return ""; }
    return l;
  });
}

const hashOf = t => crypto.createHash("sha1")
  .update(t.replace(SOURCE_STRIP, " ").replace(/\s+/g, " ").trim().toLowerCase()).digest("hex").slice(0, 10);

// «П1–П6, П9» → [{id, ranged}]: в диапазоне удалённые номера не ошибка, одиночный номер обязан существовать.
function expandIds(s) {
  const out = [], re = /П(\d+)(?:\s*[–—-]\s*П?(\d+))?/g;
  let m;
  while ((m = re.exec(String(s || "")))) {
    let a = +m[1], b = m[2] ? +m[2] : a;
    if (b < a) [a, b] = [b, a];
    for (let k = a; k <= b && k - a < 500; k++) out.push({ id: "П" + k, ranged: b !== a });
  }
  return out;
}

function parse(text) {
  const lines = visibleLines(text);
  const heads = [];
  lines.forEach((l, i) => { const m = l.match(HEAD_RE); if (m) heads.push({ level: m[1].length, title: m[2], line: i }); });
  const section = re => {
    const idx = heads.findIndex(h => h.level === 2 && re.test(h.title));
    if (idx < 0) return null;
    const next = heads.slice(idx + 1).find(h => h.level <= 2);
    return { title: heads[idx].title, start: heads[idx].line + 1, end: next ? next.line : lines.length };
  };
  const body = sec => (sec ? lines.slice(sec.start, sec.end) : []);

  const fields = {};
  const firstH2 = heads.find(h => h.level === 2);
  for (const l of lines.slice(0, firstH2 ? firstH2.line : 20)) {
    const m = l.match(/^(Статус|Объём|Исполнитель):\s*(.+?)\s*$/);
    if (m) fields[m[1]] = m[2];
  }
  const h1 = heads.find(h => h.level === 1);

  // Текст пункта — всё от его номера до следующего пункта или заголовка: подсписки, таблица, второй абзац.
  const items = [];
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(ITEM_RE);
    if (!m) continue;
    const buf = [m[2].replace(/^\*\*\s*[.:]?\s*/, "")];
    for (let j = i + 1; j < lines.length && !ITEM_RE.test(lines[j]) && !HEAD_RE.test(lines[j]); j++) buf.push(lines[j].trim());
    const t = buf.join(" ").replace(/\s+/g, " ").trim();
    const src = t.match(SOURCE_RE);
    items.push({ id: m[1], line: i + 1, text: t, source: src ? src[1].toLowerCase() : "", hash: hashOf(t) });
  }
  // Строка начинается с номера, а пунктом не распознана («П5. текст» без жирного) — иначе пункт пропал бы молча.
  const lookalikes = [];
  const itemsSec = section(/пункты/i);
  if (itemsSec) for (let i = itemsSec.start; i < itemsSec.end; i++) if (ITEM_LIKE.test(lines[i]) && !ITEM_RE.test(lines[i])) lookalikes.push(i + 1);

  const stages = [];
  let through = [];
  const stSec = section(/этап/i);
  if (stSec) {
    let cur = null;
    for (let i = stSec.start; i < stSec.end; i++) {
      const h = lines[i].match(/^###\s+Этап\s+(\d+)\.?\s*(.*)$/i);
      if (h) { cur = { n: +h[1], title: h[2].trim(), ids: [], hasIds: false, check: null, where: null }; stages.push(cur); continue; }
      const f = lines[i].match(/^\s*(?:[-*]\s+)?(?:\*\*)?([А-Яа-яЁё ]+?):(?:\*\*)?\s*(.*)$/);
      if (!f) continue;
      const key = f[1].trim().toLowerCase(), val = f[2].trim();
      if (/^сквозн/.test(key)) through = through.concat(expandIds(val));
      else if (!cur) continue;
      else if (key === "пункты") { cur.ids = cur.ids.concat(expandIds(val)); cur.hasIds = true; }
      else if (key === "точка проверки") cur.check = val;
      else if (key === "где смотреть") cur.where = val;
    }
  }
  return { lines, heads, fields, title: h1 ? h1.title : "", items, lookalikes, stages, through, section, body };
}

const read = file => parse(fs.readFileSync(file, "utf8"));

// ---------------------------------------------------------------- отметки прохода

const statePath = file => file.replace(/\.md$/i, "") + ".pass.json";
function loadState(file) {
  const p = statePath(file);
  if (!fs.existsSync(p)) return { items: {} };
  let data;
  try { data = JSON.parse(fs.readFileSync(p, "utf8")); } catch {
    throw new Error(`Файл отметок ${path.basename(p)} не читается (конфликт слияния?). Почини его или удали — тогда все пункты пройдутся заново`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) data = {};
  if (!data.items || typeof data.items !== "object" || Array.isArray(data.items)) data.items = {};
  return data;
}
function saveState(file, state) { fs.writeFileSync(statePath(file), JSON.stringify(state, null, 2) + "\n"); }

// Пункт в очереди, пока не отмечен, пока его текст изменился после отметки и пока он «исправлен» или «задет».
function queue(doc, state) {
  const out = [];
  for (const it of doc.items) {
    const s = state.items[it.id];
    if (!s) out.push({ item: it, reason: "ещё не пройден" });
    else if (!s.hash) out.push({ item: it, reason: s.verdict === "исправлен" ? "исправлен — пройди заново, как в первый раз" : "задет правкой другого пункта — пройди заново" });
    else if (s.hash !== it.hash) out.push({ item: it, reason: `изменён после прохода № ${s.pass} — пройди заново` });
  }
  return out;
}

// Пункты о том же: общие основы слов. Подсказка для поиска конфликтов и задетых правкой, не приговор.
function related(doc, id) {
  const stems = t => new Set((t.toLowerCase().replace(SOURCE_STRIP, " ").match(/[а-яёa-z]{5,}/g) || []).map(w => w.slice(0, 5)));
  const all = doc.items.map(it => ({ id: it.id, stems: stems(it.text) }));
  const df = new Map();
  for (const a of all) for (const s of a.stems) df.set(s, (df.get(s) || 0) + 1);
  const common = Math.max(2, all.length * 0.35);
  const me = all.find(a => a.id === id);
  if (!me) return [];
  return all.filter(a => a.id !== id)
    .map(a => ({ id: a.id, n: [...a.stems].filter(s => me.stems.has(s) && df.get(s) <= common).length }))
    .filter(a => a.n >= 2).sort((a, b) => b.n - a.n).slice(0, 5).map(a => a.id);
}

// touch — номера пунктов строкой («П4,П11», «П2–П6») или списком.
function stamp(file, id, verdict, touch = []) {
  const doc = read(file);
  const item = doc.items.find(it => it.id === id);
  if (!item) throw new Error(`Пункта ${id} в ТЗ нет`);
  verdict = VERDICT_ALIAS[verdict] || verdict;
  if (!VERDICTS.includes(verdict)) throw new Error(`Итог — один из: ${VERDICTS.join(", ")}`);
  const refs = Array.isArray(touch) ? touch.map(t => ({ id: t, ranged: false })) : expandIds(touch);
  if (!Array.isArray(touch) && touch && !refs.length) throw new Error("--touch: не вижу номеров пунктов — пиши П4,П11 или П2–П6");
  const state = loadState(file);
  const today = new Date().toISOString().slice(0, 10);
  const prev = state.items[id];
  // «исправлен» — текст менялся: отпечаток не пишется, и пункт остаётся в очереди до итога «чисто».
  state.items[id] = { hash: verdict === "исправлен" ? "" : item.hash, pass: (prev ? prev.pass : 0) + 1, verdict, t: today };
  const touched = [];
  for (const ref of refs) {
    if (ref.id === id) continue;
    if (!doc.items.some(it => it.id === ref.id)) { if (ref.ranged) continue; throw new Error(`Задетого пункта ${ref.id} в ТЗ нет`); }
    const p = state.items[ref.id];
    state.items[ref.id] = { hash: "", pass: p ? p.pass : 0, verdict: "задет", t: today };
    touched.push(ref.id);
  }
  saveState(file, state);
  return { doc, state, verdict, touched };
}

function statusLine(doc, state) {
  const q = queue(doc, state);
  const live = doc.items.filter(it => state.items[it.id] && state.items[it.id].hash === it.hash);
  const waiting = live.filter(it => state.items[it.id].verdict === "вопрос").length;
  const repeat = live.filter(it => state.items[it.id].pass > 1).length;
  const bySource = SOURCES.map(s => [s, doc.items.filter(it => it.source === s).length]).filter(([, n]) => n)
    .map(([s, n]) => `${s} ${n}`).join(", ");
  const stops = doc.stages.filter(st => /^стоп/i.test(st.check || "")).length;
  return `Пунктов ${doc.items.length} · пройдено ${live.length - waiting} (повторно ${repeat}) · ждут ответа ${waiting}` +
    ` · в очереди ${q.length} · источники: ${bySource || "—"} · этапов ${doc.stages.length}, остановок ${stops}`;
}

// ---------------------------------------------------------------- проверка

// Корень проекта — папка, в которой лежит technical-docs; ТЗ вне этой папки — ближайший .git, иначе текущая папка.
function projectRoot(file, given) {
  if (given) return path.resolve(given);
  const abs = path.resolve(file);
  const parts = abs.split(path.sep);
  const k = parts.lastIndexOf(DOCS);
  if (k > 0) return parts.slice(0, k).join(path.sep) || path.sep;
  for (let d = path.dirname(abs); ; d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, ".git"))) return d;
    if (d === path.dirname(d)) return process.cwd();
  }
}

// Пути к файлам в обратных кавычках: с косой чертой и расширением (`todo/server.js`). Слова вроде `GET/POST`
// и `application/json` путями не считаются. Пометка «(новый)» сразу после имени — файла ещё нет.
function fileRefs(doc) {
  const refs = [];
  const re = /`([^`\n]+)`(\s*\((?:нов|будет)[^)]*\))?/g;
  doc.lines.forEach((l, i) => {
    let m;
    while ((m = re.exec(l))) {
      const p = m[1].replace(/(:\d+(-\d+)?|#L\d+(-L?\d+)?)$/, "");
      if (m[2] || !p.includes("/") || !/^[\w.-][\w.@/-]*\.[A-Za-z0-9]{1,6}$/.test(p)) continue;
      refs.push({ path: p, line: i + 1 });
    }
  });
  return refs;
}

function protocolPath(file) {
  const base = path.basename(file);
  return path.join(path.dirname(file), /^tz_/.test(base) ? base.replace(/^tz_/, "protocol_") : base.replace(/\.md$/i, "") + ".protocol.md");
}

// Раздел протокола тянется до следующего раздела протокола: ответ читателя приходит со своими заголовками.
function protocolSection(text, re) {
  const lines = visibleLines(text);
  const heads = [];
  lines.forEach((l, i) => { const m = l.match(/^##\s+(.*?)\s*$/); if (m) heads.push({ title: m[1], line: i }); });
  const idx = heads.findIndex(h => re.test(h.title));
  if (idx < 0) return "";
  const next = heads.slice(idx + 1).find(h => PROTOCOL_HEADS.some(r => r.test(h.title)));
  return lines.slice(heads[idx].line + 1, next ? next.line : lines.length).join("\n");
}

const isNothing = l => /^[—–-]$/.test(l) || (/^нет(?![а-яё])/i.test(l) && !l.includes("?"));

function check(file, opts = {}) {
  const doc = read(file);
  const state = loadState(file);
  const E = [], W = [];

  for (const [name, re] of REQUIRED) if (!doc.section(re)) E.push(`нет раздела «${name}»`);
  if (!doc.items.length) E.push("нет ни одного пункта: пункт начинается с «**П1.**» и несёт источник, например [владелец]");
  for (const n of doc.lookalikes) E.push(`строка ${n}: похоже на пункт, но номер не распознан — пиши «**П5.** текст»`);

  const seen = new Map();
  for (const it of doc.items) {
    if (seen.has(it.id)) E.push(`${it.id} встречается дважды (строки ${seen.get(it.id)} и ${it.line}): номера не переиспользуются`);
    seen.set(it.id, it.line);
    if (!it.source) E.push(`${it.id}: нет источника — ${SOURCES.map(s => `[${s}]`).join(", ")}`);
    const vague = [...new Set((it.text.replace(SOURCE_STRIP, " ").match(VAGUE) || []).map(s => s.toLowerCase()))];
    if (vague.length) W.push(`${it.id}: расплывчато — «${vague.join("», «")}»: замени числом или признаком, который можно показать`);
  }

  const placed = new Map();
  const place = (ref, where) => {
    if (!seen.has(ref.id)) { if (!ref.ranged) E.push(`${where} ссылается на ${ref.id}, которого в ТЗ нет`); return; }
    if (placed.has(ref.id)) E.push(`${ref.id} стоит в двух местах: ${placed.get(ref.id)} и ${where}`);
    else placed.set(ref.id, where);
  };
  doc.through.forEach(ref => place(ref, "сквозные пункты"));
  if (doc.section(/этап/i) && !doc.stages.length) E.push("в разделе этапов нет ни одного «### Этап 1. …»");
  doc.stages.forEach((st, idx) => {
    const name = `этап ${st.n}`;
    if (!st.hasIds) E.push(`${name}: нет строки «Пункты: …»`);
    else if (!st.ids.length) E.push(`${name}: в строке «Пункты» не вижу номеров — пиши «П1–П4, П9»`);
    st.ids.forEach(ref => place(ref, name));
    const c = st.check || "";
    if (!c) E.push(`${name}: не решено, есть ли точка проверки — «Точка проверки: стоп — …» или «без остановки — причина»`);
    else if (/^стоп/i.test(c)) {
      if (!st.where || /^[<…]|^\.\.\.$/.test(st.where)) E.push(`${name}: остановка без «Где смотреть: …» — адрес стенда или тестового сервера, файл или команда`);
    } else if (/^без остановки/i.test(c)) {
      if (c.replace(/^без остановки[\s—–:,-]*/i, "").length < 5) E.push(`${name}: «без остановки» без причины`);
    } else E.push(`${name}: «Точка проверки» начинается со слова «стоп» или «без остановки»`);
    if (idx === doc.stages.length - 1 && c && !/^стоп/i.test(c)) E.push(`${name}: последний этап всегда кончается остановкой — это приёмка`);
  });
  if (doc.stages.length) for (const it of doc.items) if (!placed.has(it.id)) E.push(`${it.id} не попал ни в один этап`);

  const root = projectRoot(file, opts.root), own = path.dirname(path.resolve(file));
  for (const ref of fileRefs(doc)) {
    if (fs.existsSync(path.join(root, ref.path)) || fs.existsSync(path.join(own, ref.path))) continue;
    E.push(`строка ${ref.line}: файла \`${ref.path}\` нет (новый файл помечай «(новый)» сразу после имени)`);
  }

  const small = /^малое/i.test(doc.fields["Объём"] || "");
  const steps = doc.body(doc.section(/увидите|сценарий/i)).filter(l => /^\s*\d+[.)]\s+\S/.test(l)).length;
  if (doc.section(/увидите|сценарий/i) && steps < 3) W.push("в сценарии «Что вы увидите» меньше трёх шагов — пункты не из чего выводить");
  if (small && doc.items.length > LIMIT_SMALL) W.push(`малое ТЗ, а пунктов ${doc.items.length}: больше ${LIMIT_SMALL} — это уже полное, с читателями и рецензентом простоты`);
  if (doc.items.length > LIMIT_ITEMS) W.push(`пунктов ${doc.items.length} — больше ${LIMIT_ITEMS}: предложи владельцу разрезать на два ТЗ`);
  if (doc.stages.length > LIMIT_STAGES) W.push(`этапов ${doc.stages.length} — больше ${LIMIT_STAGES}: предложи владельцу разрезать на два ТЗ`);
  const guessed = doc.items.filter(it => it.source === "допущение").map(it => it.id);
  if (doc.items.length >= 6 && guessed.length * 3 > doc.items.length) W.push(`больше трети пунктов — твои допущения (${guessed.join(", ")}): покажи список владельцу`);

  if (opts.launch) {
    for (const q of queue(doc, state)) E.push(`${q.item.id}: ${q.reason}`);
    for (const it of doc.items) {
      const s = state.items[it.id];
      if (s && s.hash === it.hash && s.verdict === "вопрос") E.push(`${it.id}: ждёт ответа владельца`);
    }
    const open = doc.body(doc.section(/открытые вопросы/i)).map(l => l.trim()).filter(l => l && !isNothing(l));
    if (open.length) E.push(`в «Открытых вопросах» ${open.length} строк — ТЗ с неотвеченными вопросами не запускается`);
    if (!small) {
      const pf = protocolPath(file);
      if (!fs.existsSync(pf)) E.push(`нет протокола прохода ${path.basename(pf)} — у полного ТЗ в нём ответы двух читателей и рецензента простоты`);
      else {
        const text = fs.readFileSync(pf, "utf8");
        for (const [name, re] of READERS) {
          if (protocolSection(text, re).replace(/\s/g, "").length < 80) E.push(`в протоколе пуст раздел «${name}»`);
        }
      }
    }
  }
  return { doc, state, errors: E, warnings: W };
}

// ---------------------------------------------------------------- папка и оглавление

const PROTOCOL = small => `# Протокол прохода: {{имя}}

Что нашли в ТЗ и что с этим сделали. Ответы читателей и рецензента — целиком, как пришли.
${small ? "" : "\n## Читатель 1\n\n## Читатель 2\n\n## Рецензент простоты\n"}
## Находки и что с ними сделано

| Пункт | Что нашли | Кто нашёл | Путь | Итог |
|---|---|---|---|---|

## Вопросы и ответы

| № | Дата | Вопрос | Варианты | Ответ |
|---|---|---|---|---|

## Правки на точках проверки

| Этап | Что поправил владелец | Вид пропуска |
|---|---|---|
`;

function tzFiles(root) {
  const base = path.join(root, DOCS);
  if (!fs.existsSync(base)) return [];
  const out = [];
  for (const e of fs.readdirSync(base, { withFileTypes: true })) {
    if (e.isFile() && /^tz_.*\.md$/.test(e.name)) out.push(e.name);
    if (!e.isDirectory()) continue;
    for (const f of fs.readdirSync(path.join(base, e.name))) if (/^tz_.*\.md$/.test(f)) out.push(path.join(e.name, f));
  }
  return out.sort();
}

function buildIndex(root) {
  const base = path.join(root, DOCS);
  const cell = s => String(s || "—").replace(/\|/g, "/").replace(/\s+/g, " ").trim();
  const rows = tzFiles(root).map(rel => {
    const text = fs.readFileSync(path.join(base, rel), "utf8");
    const doc = parse(text);
    const date = (text.slice(0, 600).match(/\d{2}\.\d{2}\.\d{4}/) || ["—"])[0];
    const brief = doc.body(doc.section(/коротко/i)).map(l => l.trim()).find(Boolean) || "";
    const title = doc.title.replace(/^ТЗ:\s*/i, "").trim() || rel;
    return `| [${cell(title)}](${rel.split(path.sep).join("/")}) | ${cell(doc.fields["Статус"])} | ${date} | ${cell(brief).slice(0, 140)} |`;
  });
  const block = [INDEX_START, "| Техзадание | Статус | Дата | Коротко |", "|---|---|---|---|", ...rows, INDEX_END].join("\n");
  const file = path.join(base, "README.md");
  const intro = "# Техдокументы проекта\n\nОдна папка — одно техзадание: само ТЗ (`tz_<имя>.md`), протокол прохода (`protocol_<имя>.md`), наброски и сырьё.\n" +
    "Папку ведёт навык spec-write. Таблица собирается командой `tz.js index` — руками не править; свои документы кладите рядом.\n\n";
  let text = intro + block + "\n";
  if (fs.existsSync(file)) {
    text = fs.readFileSync(file, "utf8");
    const a = text.indexOf(INDEX_START), b = a < 0 ? -1 : text.indexOf(INDEX_END, a);
    if (a >= 0 && b > a) text = text.slice(0, a) + block + text.slice(b + INDEX_END.length);
    else if (a >= 0 || text.includes(INDEX_END)) throw new Error(`В ${DOCS}/README.md потерян один из маркеров оглавления («${INDEX_START}» … «${INDEX_END}»). Верни его: чужой текст программа не трогает`);
    else text = text.replace(/\s*$/, "\n\n") + block + "\n";
  }
  fs.mkdirSync(base, { recursive: true });
  fs.writeFileSync(file, text);
  return { file, count: rows.length };
}

function create(name, opts = {}) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name || "")) throw new Error("Имя папки — латиницей через дефис: council, super-body");
  const root = path.resolve(opts.root || ".");
  const dir = path.join(root, DOCS, name);
  if (fs.existsSync(dir)) throw new Error(`Папка ${path.join(DOCS, name)} уже есть — дорабатывай ТЗ в ней`);
  const d = new Date();
  const today = [d.getDate(), d.getMonth() + 1].map(n => String(n).padStart(2, "0")).join(".") + "." + d.getFullYear();
  const fill = s => s.replace(/\{\{имя\}\}/g, name).replace(/\{\{дата\}\}/g, today);
  let tpl = fill(fs.readFileSync(path.join(__dirname, "TEMPLATE.md"), "utf8"));
  if (opts.small) tpl = tpl.replace(/^Объём: полное$/m, "Объём: малое");
  fs.mkdirSync(dir, { recursive: true });
  const tz = path.join(dir, `tz_${name}.md`);
  fs.writeFileSync(tz, tpl);
  fs.writeFileSync(path.join(dir, `protocol_${name}.md`), fill(PROTOCOL(opts.small)));
  buildIndex(root);
  return tz;
}

// ---------------------------------------------------------------- команды

function printNext(doc, state) {
  const q = queue(doc, state);
  if (!q.length) { console.log("Очередь пуста. " + statusLine(doc, state)); return; }
  const { item, reason } = q[0];
  console.log(`${item.id} — ${reason} (в очереди ${q.length})`);
  console.log(item.text);
  const rel = related(doc, item.id);
  if (rel.length) console.log(`Возможно связаны: ${rel.join(", ")}`);
}

const FLAGS = { new: ["root", "small"], check: ["root", "launch"], next: [], stamp: ["touch"], status: [], index: ["root"] };

function main(argv) {
  const [cmd, ...rest] = argv;
  const flags = {}, args = [];
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i], eq = a.match(/^--([a-z]+)=(.*)$/);
    if (eq) flags[eq[1]] = eq[2];
    else if (a === "--root" || a === "--touch") flags[a.slice(2)] = rest[++i] || "";
    else if (a.startsWith("--")) flags[a.slice(2)] = true;
    else args.push(a);
  }
  const need = () => {
    if (!args[0]) fail("Укажи файл ТЗ");
    if (!fs.existsSync(args[0])) fail(`Файла ${args[0]} нет`);
    return args[0];
  };
  try {
    if (!FLAGS[cmd]) fail("Команды: new <имя> · check <ТЗ> [--launch] · next <ТЗ> · stamp <ТЗ> <П7> <итог> [--touch П4,П11] · status <ТЗ> · index");
    const unknown = Object.keys(flags).filter(f => !FLAGS[cmd].includes(f));
    if (unknown.length) fail(`У команды ${cmd} нет ключа --${unknown[0]}${FLAGS[cmd].length ? `; есть: ${FLAGS[cmd].map(f => "--" + f).join(", ")}` : ""}`);
    if (cmd === "new") {
      const tz = create(args[0], flags);
      console.log(`Создано: ${path.relative(process.cwd(), tz)} и протокол рядом; оглавление — ${DOCS}/README.md`);
    } else if (cmd === "check") {
      const r = check(need(), flags);
      r.errors.forEach(e => console.log("ОШИБКА: " + e));
      r.warnings.forEach(w => console.log("Замечание: " + w));
      console.log(statusLine(r.doc, r.state));
      console.log(r.errors.length ? `Ошибок: ${r.errors.length}.` : flags.launch ? "ТЗ готово к запуску." : "Строение в порядке.");
      if (r.errors.length) process.exit(1);
    } else if (cmd === "next") {
      const file = need();
      printNext(read(file), loadState(file));
    } else if (cmd === "stamp") {
      const file = need();
      if ("touch" in flags && !flags.touch) fail("--touch: назови задетые пункты — П4,П11 или П2–П6");
      const r = stamp(file, args[1], args[2], flags.touch || "");
      const back = r.verdict === "исправлен" ? [args[1], ...r.touched] : r.touched;
      console.log(`${args[1]}: ${r.verdict}${back.length ? `; в очереди снова: ${back.join(", ")}` : ""}. Дальше:`);
      printNext(r.doc, r.state);
    } else if (cmd === "status") {
      const file = need();
      console.log(statusLine(read(file), loadState(file)));
    } else if (cmd === "index") {
      const r = buildIndex(path.resolve(flags.root || "."));
      console.log(`Оглавление: ${path.relative(process.cwd(), r.file)}, техзаданий — ${r.count}`);
    }
  } catch (e) { fail(e.message); }
}

if (require.main === module) main(process.argv.slice(2));
module.exports = { parse, check, queue, related, stamp, statusLine, create, buildIndex, loadState, VERDICTS, SOURCES };
