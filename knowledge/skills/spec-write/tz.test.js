// Проверки программы техзаданий: node tz.test.js — хорошее ТЗ проходит, каждая поломка ловится.
"use strict";
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const tz = require("./tz.js");

const GOOD = `# ТЗ: Корзина заметок

Версия 1 · 13.11.2026 · автор — агент по просьбе владельца
Статус: проход
Объём: малое
Исполнитель: агент

## Коротко

Удалённые заметки лежат в корзине 30 дней, их можно вернуть.

## 1. Зачем

Удалённую по ошибке заметку сейчас не вернуть.

## 2. Что вы увидите, когда готово

1. Открываю заметки и нажимаю «Удалить» у заметки.
2. Заметка исчезает из списка, внизу строка «Заметка в корзине» с кнопкой «Вернуть».
3. Открываю «Корзину» и вижу удалённую заметку с датой.

## 3. Чего не делаем

Поиска по корзине.

## 4. Как этим пользуются

Главное действие корзины — «Вернуть».

## 5. Пункты задания

**П1.** Когда человек нажимает «Удалить» у заметки, заметка исчезает из списка и попадает в корзину. *[владелец]*
**П2.** Когда заметка попала в корзину, внизу 5 секунд видна строка «Заметка в корзине» с кнопкой «Вернуть». *[решение]*
- **П3.** Корзина показывает удалённые заметки с датой удаления,
  новые сверху. *[допущение: как в списке заметок]*

**П4.** Заметка лежит в корзине 30 дней, потом удаляется навсегда. *[владелец]*
**П5.** Корзину видит только владелец заметок. *[защита]*

## 6. Принятые риски

Нет.

## 7. Памятка исполнителю

Код — \`app/notes.js\`, страница корзины — \`app/trash.js\` (новый). Запросы — \`GET/POST\`, ответ \`application/json\`,
ветка \`origin/main\`, значения \`true/false\`, пакет \`@types/node\`.

\`\`\`
**П9.** Пример в заборе кода пунктом не считается.
~~~
\`\`\`

## 8. Этапы и точки проверки

Сквозные пункты: П5

### Этап 1. Удаление в корзину

- Пункты: П1–П2
- Точка проверки: стоп — шаги 1–2 сценария
- Где смотреть: http://127.0.0.1:5190/notes.html

### Этап 2. Страница корзины

- Пункты: П3, П4
- Точка проверки: стоп — весь сценарий
- Где смотреть: http://127.0.0.1:5190/trash.html

## 9. Решения владельца

| № | Дата | Вопрос | Ответ | Отвергнуто | Пункты |
|---|---|---|---|---|---|

## 10. Открытые вопросы

Нет.
`;

const made = [];
const tmp = () => { const d = fs.mkdtempSync(path.join(os.tmpdir(), "tz-test-")); made.push(d); return d; };
function project(text, { git = true } = {}) {
  const root = tmp();
  if (git) fs.mkdirSync(path.join(root, ".git"));
  fs.mkdirSync(path.join(root, "app"));
  fs.writeFileSync(path.join(root, "app", "notes.js"), "");
  const dir = path.join(root, "technical-docs", "trash");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, "tz_trash.md");
  fs.writeFileSync(file, text);
  return { root, file, dir };
}
const errorsOf = (text, opts) => tz.check(project(text).file, opts).errors;
const swap = (from, to) => { assert(GOOD.includes(from), "в образце нет строки: " + from); return GOOD.replace(from, to); };
const has = (list, re) => assert(list.some(s => re.test(s)), `нет ожидаемого «${re}» в:\n  ${list.join("\n  ") || "(пусто)"}`);
const stampAll = (file, verdict = "чисто") => ["П1", "П2", "П3", "П4", "П5"].forEach(id => tz.stamp(file, id, verdict));
const queueOf = file => tz.queue(tz.parse(fs.readFileSync(file, "utf8")), tz.loadState(file));
const edit = (file, from, to) => { const t = fs.readFileSync(file, "utf8"); assert(t.includes(from), "нет строки: " + from); fs.writeFileSync(file, t.replace(from, to)); };
const cli = (...args) => spawnSync(process.execPath, [path.join(__dirname, "tz.js"), ...args], { encoding: "utf8" });

const tests = {
  "хорошее ТЗ проходит без ошибок и замечаний"() {
    const r = tz.check(project(GOOD).file);
    assert.deepStrictEqual(r.errors, []);
    assert.deepStrictEqual(r.warnings, []);
    assert.strictEqual(r.doc.items.length, 5, "пример в заборе кода — не пункт");
    assert.strictEqual(r.doc.items[2].text.includes("новые сверху"), true, "продолжение пункта на второй строке");
  },
  "пункт без этапа"() { has(errorsOf(swap("- Пункты: П3, П4", "- Пункты: П3")), /П4 не попал ни в один этап/); },
  "этап ссылается на несуществующий пункт"() { has(errorsOf(swap("- Пункты: П3, П4", "- Пункты: П3, П4, П77")), /ссылается на П77/); },
  "пункт в двух этапах"() { has(errorsOf(swap("- Пункты: П3, П4", "- Пункты: П2, П3, П4")), /П2 стоит в двух местах/); },
  "диапазон задом наперёд и строка «Пункты» без номеров"() {
    assert.deepStrictEqual(errorsOf(swap("- Пункты: П1–П2", "- Пункты: П2–П1")), []);
    has(errorsOf(swap("- Пункты: П1–П2", "- Пункты: первый и второй")), /этап 1: в строке «Пункты» не вижу номеров/);
  },
  "этап без решения о точке проверки"() { has(errorsOf(swap("- Точка проверки: стоп — весь сценарий\n", "")), /этап 2: не решено/); },
  "остановка без «где смотреть»"() { has(errorsOf(swap("- Где смотреть: http://127.0.0.1:5190/notes.html\n", "")), /этап 1: остановка без «Где смотреть/); },
  "«где смотреть» не заполнено"() { has(errorsOf(swap("http://127.0.0.1:5190/notes.html", "…")), /этап 1: остановка без/); },
  "«без остановки» без причины"() { has(errorsOf(swap("стоп — шаги 1–2 сценария", "без остановки")), /этап 1: «без остановки» без причины/); },
  "«без остановки» с причиной — можно, но не на последнем этапе"() {
    assert.deepStrictEqual(errorsOf(swap("стоп — шаги 1–2 сценария", "без остановки — смотреть нечего, итог виден на этапе 2")), []);
    has(errorsOf(swap("стоп — весь сценарий", "без остановки — внутренний этап")), /последний этап всегда кончается остановкой/);
  },
  "ссылка на несуществующий файл; «(новый)» — не ошибка; слова с косой чертой — не пути"() {
    has(errorsOf(swap("`app/notes.js`", "`app/nope.js`")), /файла `app\/nope\.js` нет/);
    has(errorsOf(swap("`app/trash.js` (новый)", "`app/trash.js`")), /файла `app\/trash\.js` нет/);
    assert.strictEqual(errorsOf(GOOD).filter(e => /файла/.test(e)).length, 0, "GET/POST, application/json, origin/main — не файлы");
  },
  "корень проекта — папка над technical-docs, даже без .git; материалы рядом с ТЗ находятся"() {
    const p = project(swap("`app/trash.js` (новый)", "`app/trash.js` (новый), набросок — `mockups/trash.png`"), { git: false });
    has(tz.check(p.file).errors, /файла `mockups\/trash\.png` нет/);
    fs.mkdirSync(path.join(p.dir, "mockups"));
    fs.writeFileSync(path.join(p.dir, "mockups", "trash.png"), "");
    assert.deepStrictEqual(tz.check(p.file).errors, [], "app/notes.js найден от корня без .git, набросок — от папки ТЗ");
  },
  "номер дважды и пункт без источника"() {
    has(errorsOf(swap("**П2.**", "**П1.**")), /П1 встречается дважды/);
    has(errorsOf(swap("попадает в корзину. *[владелец]*", "попадает в корзину.")), /П1: нет источника/);
  },
  "пункт распознаётся в разных формах; номер без жирного — ошибка, а не тихая пропажа"() {
    const forms = ["1. **П4.** Заметка", "**П4. Срок.** Заметка", "**П4**. Заметка", "**П4:** Заметка", "+ **П4.** Заметка", "> **П4.** Заметка"];
    for (const f of forms) {
      const r = tz.check(project(swap("**П4.** Заметка", f)).file);
      assert.deepStrictEqual(r.errors, [], "форма: " + f);
      assert.strictEqual(r.doc.items.length, 5, "форма: " + f);
    }
    has(errorsOf(swap("**П4.** Заметка", "П4. Заметка")), /строка \d+: похоже на пункт, но номер не распознан/);
    const range = tz.check(project(swap("**П5.** Корзину", "**П1–П4** — про корзину.\n\n**П5.** Корзину")).file);
    assert.strictEqual(range.doc.items.length, 5, "«**П1–П4**» — ссылка на диапазон, не пункт");
  },
  "текст пункта — до следующего пункта: подсписок после пустой строки, таблица, источник в конце"() {
    const text = swap("**П4.** Заметка лежит в корзине 30 дней, потом удаляется навсегда. *[владелец]*",
      "**П4.** У заметки в корзине видно:\n\n- дату удаления;\n- кнопку «Вернуть».\n\n| Срок | Дней |\n|---|---|\n| хранение | 30 |\n\n*[владелец]*");
    const { file } = project(text);
    assert.deepStrictEqual(tz.check(file).errors, [], "источник в конце подсписка найден");
    stampAll(file);
    edit(file, "- кнопку «Вернуть».", "- кнопку «Удалить навсегда» без подтверждения.");
    assert.deepStrictEqual(queueOf(file).map(x => x.item.id), ["П4"], "правка подсписка возвращает пункт в очередь");
    tz.stamp(file, "П4", "чисто");
    edit(file, "| хранение | 30 |", "| хранение | 30000 |");
    assert.deepStrictEqual(queueOf(file).map(x => x.item.id), ["П4"], "правка таблицы пункта возвращает пункт в очередь");
  },
  "нет обязательного раздела"() {
    has(errorsOf(swap("## 4. Как этим пользуются", "## 4. Прочее")), /нет раздела «Как этим пользуются»/);
    has(errorsOf(swap("## 2. Что вы увидите, когда готово", "## 2. Описание")), /нет раздела «Что вы увидите/);
  },
  "расплывчатое слово — замечание, не ошибка"() {
    const r = tz.check(project(swap("новые сверху.", "новые сверху, чтобы было удобно.")).file);
    assert.deepStrictEqual(r.errors, []);
    has(r.warnings, /П3: расплывчато — «удобно»/);
  },
  "малое ТЗ, разросшееся за 14 пунктов, — замечание"() {
    const extra = Array.from({ length: 10 }, (_, i) => `**П${20 + i}.** Строка ${i + 1} списка показывает дату создания заметки. *[допущение: как в списке]*`).join("\n\n");
    const text = swap("## 6. Принятые риски", extra + "\n\n## 6. Принятые риски").replace("- Пункты: П3, П4", "- Пункты: П3, П4, П20–П29");
    const r = tz.check(project(text).file);
    assert.deepStrictEqual(r.errors, []);
    has(r.warnings, /малое ТЗ, а пунктов 15/);
    has(r.warnings, /больше трети пунктов — твои допущения/);
  },
  "концы строк Windows и метка BOM не ломают разбор"() {
    const r = tz.check(project("﻿" + GOOD.replace(/\n/g, "\r\n")).file);
    assert.deepStrictEqual(r.errors, []);
    assert.strictEqual(r.doc.items.length, 5);
    assert.strictEqual(r.doc.title, "ТЗ: Корзина заметок");
  },
  "забор в заборе: ~~~ внутри ``` и ``` внутри ```` не открывают и не закрывают лишнего"() {
    const text = swap("```\n**П9.** Пример в заборе кода пунктом не считается.\n~~~\n```",
      "````\n```\n**П9.** Пример во вложенном заборе пунктом не считается.\n```\n````");
    const r = tz.check(project(text).file);
    assert.deepStrictEqual(r.errors, []);
    assert.strictEqual(r.doc.items.length, 5);
  },
  "очередь: исправленный пункт проходится заново и уходит только с итогом «чисто»"() {
    const { file } = project(GOOD);
    assert.strictEqual(queueOf(file).length, 5);
    has(tz.check(file, { launch: true }).errors, /П1: ещё не пройден/);
    stampAll(file);
    assert.strictEqual(queueOf(file).length, 0);
    assert.deepStrictEqual(tz.check(file, { launch: true }).errors, [], "малое ТЗ запускается без читателей");
    edit(file, "лежит в корзине 30 дней", "лежит в корзине 14 дней");
    let q = queueOf(file);
    assert.deepStrictEqual(q.map(x => x.item.id), ["П4"]);
    assert.match(q[0].reason, /изменён после прохода № 1/);
    has(tz.check(file, { launch: true }).errors, /П4: изменён после прохода/);
    tz.stamp(file, "П4", "исправлен");
    q = queueOf(file);
    assert.deepStrictEqual(q.map(x => x.item.id), ["П4"], "«исправлен» из очереди не убирает");
    assert.match(q[0].reason, /исправлен — пройди заново/);
    has(tz.check(file, { launch: true }).errors, /П4: исправлен — пройди заново/);
    assert.throws(() => tz.stamp(file, "П4", "уточнён"), /Итог — один из: чисто, исправлен, вопрос, показ/);
    tz.stamp(file, "П4", "чисто");
    assert.deepStrictEqual(tz.check(file, { launch: true }).errors, []);
    assert.match(tz.statusLine(tz.parse(fs.readFileSync(file, "utf8")), tz.loadState(file)), /пройдено 5 \(повторно 1\)/);
  },
  "смена одного источника пункт в очередь не возвращает"() {
    const { file } = project(GOOD);
    stampAll(file);
    edit(file, "*[допущение: как в списке заметок]*", "*[решение]*");
    assert.deepStrictEqual(tz.check(file, { launch: true }).errors, []);
  },
  "задетые правкой пункты возвращаются в очередь: списком, строкой, диапазоном с дыркой"() {
    const { file } = project(GOOD);
    stampAll(file);
    tz.stamp(file, "П1", "исправлен", ["П2"]);
    const q = queueOf(file);
    assert.deepStrictEqual(q.map(x => x.item.id), ["П1", "П2"]);
    assert.match(q[1].reason, /задет правкой/);
    stampAll(file);
    const noP3 = fs.readFileSync(file, "utf8").replace(/- \*\*П3\.\*\*[\s\S]*?\n\n/, "").replace("- Пункты: П3, П4", "- Пункты: П4");
    fs.writeFileSync(file, noP3);
    assert.deepStrictEqual(tz.stamp(file, "П5", "чисто", "П2–П4").touched, ["П2", "П4"], "удалённый П3 в диапазоне — не ошибка");
    assert.throws(() => tz.stamp(file, "П1", "чисто", "4,11"), /не вижу номеров пунктов/);
    assert.throws(() => tz.stamp(file, "П1", "исправлен", ["П99"]), /Задетого пункта П99/);
    assert.throws(() => tz.stamp(file, "П1", "готово"), /Итог — один из/);
    assert.throws(() => tz.stamp(file, "П42", "чисто"), /Пункта П42/);
  },
  "пункт ждёт ответа владельца — запуска нет"() {
    const { file } = project(GOOD);
    stampAll(file);
    tz.stamp(file, "П4", "вопрос");
    const r = tz.check(file, { launch: true });
    has(r.errors, /П4: ждёт ответа владельца/);
    assert.match(tz.statusLine(r.doc, r.state), /ждут ответа 1/);
  },
  "неотвеченные вопросы — запуска нет; «Нет — все закрыты» — не вопрос"() {
    const open = GOOD.replace(/## 10\. Открытые вопросы\n\nНет\./, "## 10. Открытые вопросы\n\n1. Сколько дней хранить?");
    let p = project(open);
    stampAll(p.file);
    has(tz.check(p.file, { launch: true }).errors, /в «Открытых вопросах» есть неотвеченное/);
    p = project(GOOD.replace(/## 10\. Открытые вопросы\n\nНет\./, "## 10. Открытые вопросы\n\nНет — все закрыты 13.11.2026."));
    stampAll(p.file);
    assert.deepStrictEqual(tz.check(p.file, { launch: true }).errors, []);
    p = project(GOOD.replace(/## 10\. Открытые вопросы\n\nНет\./, "## 10. Открытые вопросы\n\nНет ли смысла хранить дольше?"));
    stampAll(p.file);
    has(tz.check(p.file, { launch: true }).errors, /в «Открытых вопросах» есть неотвеченное/);
  },
  "полное ТЗ без читателей и рецензента не запускается; их заголовки раздел не обрывают"() {
    const { file } = project(swap("Объём: малое", "Объём: полное"));
    stampAll(file);
    has(tz.check(file, { launch: true }).errors, /нет протокола прохода protocol_trash\.md/);
    const pf = path.join(path.dirname(file), "protocol_trash.md");
    const reader = "## Как понял — по пунктам\n\nП1. Построю: удаление заметки в корзину. Додумал: срок показа строки с кнопкой «Вернуть».\n\n## Вердикт\n\nСТРОИТЬ.\n";
    fs.writeFileSync(pf, `# Протокол\n\n## Читатель 1\n\n${reader}\n## Читатель 2\n\n${reader}\n## Рецензент простоты\n\n## Находки и что с ними сделано\n\n| Пункт | Что нашли |\n|---|---|\n| П1 | длинная строка таблицы, которая не должна засчитаться рецензенту простоты как его ответ |\n`);
    const errs = tz.check(file, { launch: true }).errors;
    has(errs, /пуст раздел «Рецензент простоты»/);
    assert(!errs.some(e => /Читатель/.test(e)), "ответ читателя со своими заголовками второго уровня — не пустой раздел");
    fs.writeFileSync(pf, fs.readFileSync(pf, "utf8").replace("## Рецензент простоты\n", "## Рецензент простоты\n\n## Вердикт: УПРОСТИТЬ — простота 6/10\n\nУбрать настройки корзины, оставить одну кнопку «Вернуть» и подпись о сроке хранения.\n"));
    assert.deepStrictEqual(tz.check(file, { launch: true }).errors, []);
  },
  "малое ТЗ с экраном ждёт рецензента простоты; раздел удалён — экрана нет, запуск разрешён"() {
    const { file, dir } = project(GOOD);
    stampAll(file);
    const pf = path.join(dir, "protocol_trash.md");
    fs.writeFileSync(pf, "# Протокол\n\n## Рецензент простоты\n\n<!-- подсказка -->\n\n## Находки и что с ними сделано\n\n| Пункт | Что нашли |\n|---|---|\n");
    has(tz.check(file, { launch: true }).errors, /пуст раздел «Рецензент простоты» — у ТЗ без экрана удали этот раздел/);
    fs.writeFileSync(pf, "# Протокол\n\n## Находки и что с ними сделано\n");
    assert.deepStrictEqual(tz.check(file, { launch: true }).errors, []);
    fs.writeFileSync(pf, "# Протокол\n\n## Рецензент простоты\n\n### Вердикт: УПРОСТИТЬ — простота 8/10\n\nНа телефоне клавиатура закрывает найденное; на пустой странице поле поиска перехватывает первую заметку.\n");
    assert.deepStrictEqual(tz.check(file, { launch: true }).errors, []);
  },
  "испорченный файл отметок не перезаписывается молча; пустой — не роняет"() {
    const { file } = project(GOOD);
    stampAll(file);
    const pass = file.replace(/\.md$/, ".pass.json");
    const broken = "<<<<<<< HEAD\n" + fs.readFileSync(pass, "utf8") + "=======\n{}\n>>>>>>> other\n";
    fs.writeFileSync(pass, broken);
    assert.throws(() => tz.stamp(file, "П1", "чисто"), /не читается \(конфликт слияния\?\)/);
    assert.throws(() => tz.check(file), /не читается/);
    assert.strictEqual(fs.readFileSync(pass, "utf8"), broken, "файл с конфликтом остался как был");
    fs.writeFileSync(pass, "{}");
    assert.strictEqual(queueOf(file).length, 5);
    assert.deepStrictEqual(tz.check(file).errors, []);
  },
  "новая папка ТЗ: файлы, оглавление, незаполненный шаблон не проходит"() {
    const root = tmp();
    const file = tz.create("council", { root });
    assert.strictEqual(path.relative(root, file), path.join("technical-docs", "council", "tz_council.md"));
    assert(fs.existsSync(path.join(root, "technical-docs", "council", "protocol_council.md")));
    const readmePath = path.join(root, "technical-docs", "README.md");
    const readme = fs.readFileSync(readmePath, "utf8");
    assert.match(readme, /\[council\]\(council\/tz_council\.md\) \| черновик \|/);
    const errs = tz.check(file).errors;
    has(errs, /нет ни одного пункта/);
    has(errs, /этап 1: в строке «Пункты» не вижу номеров/);
    has(errs, /этап 1: остановка без «Где смотреть/);
    assert.throws(() => tz.create("council", { root }), /уже есть/);
    assert.throws(() => tz.create("Мой раздел", { root }), /латиницей/);
    const small = tz.create("tiny", { root, small: true, title: "Поиск в заметках" });
    assert.match(fs.readFileSync(small, "utf8"), /^# ТЗ: Поиск в заметках\n[\s\S]*^Объём: малое$/m);
    const tinyProtocol = path.join(path.dirname(small), "protocol_tiny.md");
    assert(!/читател/i.test(fs.readFileSync(tinyProtocol, "utf8")), "малому ТЗ читатели не нужны");
    assert.match(fs.readFileSync(tinyProtocol, "utf8"), /^## Рецензент простоты$/m);
    fs.writeFileSync(readmePath, readme.replace("# Техдокументы проекта", "# Техдокументы проекта\n\nСвоя строка владельца.") + "\nВажное после таблицы.\n");
    assert.strictEqual(tz.buildIndex(root).count, 2);
    const again = fs.readFileSync(readmePath, "utf8");
    assert.match(again, /Своя строка владельца/);
    assert.match(again, /Важное после таблицы/);
    assert.strictEqual(again.match(/tz-index:start/g).length, 1);
    assert.match(again, /\[Поиск в заметках\]\(tiny\/tz_tiny\.md\)/);
    fs.writeFileSync(readmePath, again.replace("<!-- tz-index:end -->", ""));
    assert.throws(() => tz.buildIndex(root), /потерян один из маркеров оглавления/);
    assert.match(fs.readFileSync(readmePath, "utf8"), /Важное после таблицы/, "при потерянном маркере чужой текст не тронут");
  },
  "команды: ключ со знаком равно, неизвестный ключ, --touch без номеров"() {
    const { file } = project(GOOD);
    stampAll(file);
    let r = cli("stamp", file, "П1", "исправлен", "--touch=П2");
    assert.strictEqual(r.status, 0, r.stderr);
    assert.match(r.stdout, /П1: исправлен; в очереди снова: П1, П2/);
    r = cli("check", file, "--lanch");
    assert.strictEqual(r.status, 1);
    assert.match(r.stderr, /нет ключа --lanch/);
    r = cli("stamp", file, "П1", "чисто", "--touch");
    assert.strictEqual(r.status, 1);
    assert.match(r.stderr, /назови задетые пункты/);
    r = cli("check", file, "--launch");
    assert.strictEqual(r.status, 1);
    assert.match(r.stdout, /ОШИБКА: П2: задет правкой другого пункта/);
  },
  "«например» в пункте — замечание: пример исполнят буквально или не исполнят вовсе"() {
    has(tz.check(project(swap("новые сверху.", "новые сверху, например по дате.")).file).warnings, /П3: расплывчато — «например»/);
  },
  "файлы и команды, названные в навыке, существуют"() {
    const skill = fs.readFileSync(path.join(__dirname, "SKILL.md"), "utf8");
    for (const f of new Set(skill.match(/`[A-Za-z-]+\.(?:md|js)`/g).map(s => s.slice(1, -1)))) {
      assert(fs.existsSync(path.join(__dirname, f)), `SKILL.md называет ${f}, а рядом его нет`);
    }
    const src = fs.readFileSync(path.join(__dirname, "tz.js"), "utf8");
    for (const c of new Set(skill.match(/TZ (new|check|next|stamp|status|index)\b/g))) {
      assert(src.includes(`cmd === "${c.slice(3)}"`), `SKILL.md зовёт «${c}», а программа такой команды не знает`);
    }
    for (const v of tz.VERDICTS) assert(skill.includes("`" + v + "`"), `итог «${v}» не описан в SKILL.md`);
  },
  "несколько пунктов одной отметкой; вся очередь одной командой; длинный пункт — замечание"() {
    const { file } = project(GOOD);
    assert.deepStrictEqual(tz.stamp(file, "П1,П2, П3", "чисто").ids, ["П1", "П2", "П3"]);
    assert.deepStrictEqual(queueOf(file).map(x => x.item.id), ["П4", "П5"]);
    assert.throws(() => tz.stamp(file, "П4,П77", "чисто"), /Пункта П77 в ТЗ нет/);
    assert.deepStrictEqual(queueOf(file).map(x => x.item.id), ["П4", "П5"], "отметка с несуществующим пунктом не пишется вовсе");
    const all = cli("next", file, "--all");
    assert.match(all.stdout, /П4 — ещё не пройден\n[\s\S]*П5 — ещё не пройден\n[\s\S]*В очереди 2\./);
    const one = cli("next", file);
    assert.match(one.stdout, /^П4 — ещё не пройден \(в очереди 2\)/);
    assert(!/П5 —/.test(one.stdout));
    const long = tz.check(project(swap("новые сверху.", "новые сверху. " + "Каждая строка показывает название, дату и кнопку. ".repeat(10))).file);
    has(long.warnings, /П3: длинный пункт \(\d+ знаков\)/);
  },
  "очередь подсказывает, кто ссылается на пункт и кто ждёт ответа; «повторно» — только вернувшиеся после правки"() {
    const { file } = project(swap("**П5.** Корзину видит только владелец заметок.", "**П5.** Корзину (П3) и срок из П4 видит только владелец заметок."));
    assert.match(cli("next", file, "--all").stdout, /П3 — ещё не пройден\n[^\n]*\nНа него ссылаются: П5/);
    stampAll(file);
    tz.stamp(file, "П4", "вопрос");
    const r = cli("next", file);
    assert.match(r.stdout, /Очередь пуста\. .*повторно 0.*Ждут ответа владельца: П4/);
    tz.stamp(file, "П4", "чисто");
    assert.match(cli("status", file).stdout, /пройдено 5 \(повторно 0\)/, "вопрос → ответ без правки текста — не «повторно»");
  },
  "точка проверки называет шаг, которого нет в сценарии, — замечание"() {
    has(tz.check(project(swap("стоп — шаги 1–2 сценария", "стоп — шаги 1–8 сценария")).file).warnings, /этап 1: точка проверки называет шаг 8, а в сценарии шагов 3/);
  },
  "оглавление берёт первый абзац «Коротко» целиком и режет по слову"() {
    const { root, file } = project(swap("Удалённые заметки лежат в корзине 30 дней, их можно вернуть.", "Удалённые заметки лежат в корзине\n30 дней, их можно вернуть одним нажатием — и из строки внизу страницы, и со страницы корзины, пока срок не вышел.\n\nВторой абзац."));
    tz.buildIndex(root);
    const row = fs.readFileSync(path.join(root, "technical-docs", "README.md"), "utf8").split("\n").find(l => l.includes("tz_trash.md"));
    assert.match(row, /Удалённые заметки лежат в корзине 30 дней, их можно вернуть одним нажатием/);
    assert.match(row, /…\s\|$/);
    assert(!row.includes("Второй абзац"));
  },
  "допущение, уже вынесенное в вопрос владельцу, в замечание о допущениях не идёт"() {
    const extra = Array.from({ length: 4 }, (_, i) => `**П${20 + i}.** Строка ${i + 1} показывает дату создания. *[допущение: как в списке]*`).join("\n\n");
    const text = swap("## 6. Принятые риски", extra + "\n\n## 6. Принятые риски").replace("- Пункты: П3, П4", "- Пункты: П3, П4, П20–П23");
    const { file } = project(text);
    has(tz.check(file).warnings, /больше трети пунктов — твои допущения \(П3, П20, П21, П22, П23\)/);
    tz.stamp(file, "П20,П21,П22", "вопрос");
    assert(!tz.check(file).warnings.some(w => /больше трети/.test(w)), "три из пяти допущений уже у владельца");
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log("ok   " + name); } catch (e) { failed++; console.log("FAIL " + name + "\n     " + String(e.message).split("\n").join("\n     ")); }
}
for (const d of made) fs.rmSync(d, { recursive: true, force: true });
const total = Object.keys(tests).length;
console.log(failed ? `tz.js: упало ${failed} из ${total}` : `tz.js: проверок прошло ${total} из ${total}`);
process.exit(failed ? 1 : 0);
