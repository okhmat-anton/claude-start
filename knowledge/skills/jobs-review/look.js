#!/usr/bin/env node
// Глаза для ревью интерфейса: настоящий Chrome без окна через протокол DevTools, без пакетов (Node 22+).
//
//   node look.js shot <адрес> [--out папка] [--name имя] [--mobile | --both] [--frames 3]
//   node look.js run  <сценарий.json> [--out папка]
//   node look.js open <адрес>                  — обычное окно Chrome для человека, остаётся открытым
//   общие флаги: --auth auth.json   --readonly   --timeout 180
//
// auth.json — как войти:
//   {"base":"http://127.0.0.1:5190","login":{"path":"/api/auth/login","json":{"username":"…","password":"…"}}}
//   {"base":"http://127.0.0.1:5190","login":{"path":"/login","form":{"email":"…","password":"…"}}}  — HTML-форма
//   {"base":"https://сайт","bearer":"…"}  — ключ уходит только на адрес base, не на CDN и шрифты
// --readonly — всё, кроме GET/HEAD/OPTIONS, блокируется: смотреть рабочий сайт, ничего на нём не меняя.
//
// Сценарий: {"start":"/page.html","viewports":["desktop","mobile"],"steps":[…]}. Шаги:
//   {"shot":"имя","frames":1}   {"click":"text=Сохранить" | "#id"}   {"type":"#поле","text":"…","clear":true}
//   {"press":"Enter" | "End" | "Meta+ArrowRight"}   {"select":"text=кусок текста"}   {"go":"/другая.html"}
//   {"wait":"text=Готово" | "#id" | 1500,"timeout":5000}   {"scroll":600,"in":"#список"}
// Итог — кадры PNG и report.txt в папке --out: шаги, что можно нажать на экране, ошибки страницы,
// упавшие запросы, тексты диалогов. Шаг не удался — кадр «fail» и переход к следующему размеру экрана.
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const USAGE = "node look.js shot <адрес> | run <сценарий.json> | open <адрес>  [--auth auth.json] [--out папка]";
const VIEWPORTS = {
  desktop: { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false },
  mobile: { width: 390, height: 844, deviceScaleFactor: 2, mobile: true },
};
const MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const KEYS = { Enter: [13, "\r"], Escape: [27, ""], Tab: [9, ""], Backspace: [8, ""], Delete: [46, ""], Space: [32, " "],
  ArrowDown: [40, ""], ArrowUp: [38, ""], ArrowLeft: [37, ""], ArrowRight: [39, ""], Home: [36, ""], End: [35, ""],
  PageUp: [33, ""], PageDown: [34, ""] };
const MODS = { Alt: 1, Ctrl: 2, Control: 2, Meta: 4, Cmd: 4, Shift: 8 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function parseArgs(argv) {
  const pos = [], opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) pos.push(a);
    else if (["mobile", "both", "readonly"].includes(a.slice(2))) opt[a.slice(2)] = true;
    else opt[a.slice(2)] = argv[++i];
  }
  return { pos, opt };
}

function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  const known = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome",
    "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  const found = known.find((p) => fs.existsSync(p));
  if (!found) throw new Error("Chrome не найден — укажи путь в переменной CHROME");
  return found;
}

// Код, который выполняется внутри страницы. Самодостаточен: уходит в Chrome текстом через toString().
function inPage(kind, arg) {
  const INTER = 'a[href], button, input, select, textarea, [role="button"], [role="tab"], [role="link"], ' +
    '[role="menuitem"], [role="checkbox"], [role="switch"], summary, label[for], [onclick], [contenteditable="true"]';
  const vis = (el, inView) => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (r.width < 2 || r.height < 2 || s.visibility === "hidden" || s.display === "none" || +s.opacity < 0.05) return false;
    return !inView || (r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth);
  };
  const txt = (el) => (el.innerText || el.value || el.placeholder || el.getAttribute("aria-label") || el.title || el.alt || "")
    .replace(/\s+/g, " ").trim();
  const name = (el) => el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") +
    (typeof el.className === "string" && el.className.trim() ? "." + el.className.trim().split(/\s+/)[0] : "");
  const center = (el) => { const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; };
  const covered = (el) => {
    const { x, y } = center(el);
    const top = document.elementFromPoint(x, y);
    return top && top !== el && !el.contains(top) && !top.contains(el) ? name(top) : "";
  };
  const find = (q) => {
    let els;
    if (q.startsWith("text=")) {
      const t = q.slice(5).replace(/\s+/g, " ").trim().toLowerCase();
      const all = [...document.querySelectorAll(INTER + ", li, td, th, span, div, p, h1, h2, h3, h4")].filter((el) => vis(el, false));
      const low = (el) => txt(el).toLowerCase();
      els = all.filter((el) => low(el) === t);
      if (!els.length) els = all.filter((el) => low(el).includes(t));
      const area = (el) => { const r = el.getBoundingClientRect(); return r.width * r.height; };
      els.sort((a, b) => (b.matches(INTER) - a.matches(INTER)) || (area(a) - area(b)));
    } else {
      els = [...document.querySelectorAll(q)].filter((el) => vis(el, false));
    }
    return { el: els[0], count: els.length };
  };

  if (kind === "outline") {
    const items = [...document.querySelectorAll(INTER)].filter((el) => vis(el, true)).slice(0, 80)
      .map((el) => ({ el: name(el), text: txt(el).slice(0, 50), disabled: !!el.disabled, covered: covered(el) }));
    const heads = [...document.querySelectorAll("h1, h2, h3")].filter((el) => vis(el, true))
      .map((el) => txt(el).slice(0, 70)).filter(Boolean).slice(0, 10);
    const scrollers = [...document.querySelectorAll("body *")].filter((el) => {
      const s = getComputedStyle(el);
      return /(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 40 && vis(el, true);
    }).slice(0, 3).map((el) => `${name(el)} (${el.scrollHeight} px)`);
    return { title: document.title, heads, items, scrollers, pageHeight: document.documentElement.scrollHeight };
  }
  if (kind === "find") {
    const { el, count } = find(arg);
    return el ? { el: name(el), text: txt(el).slice(0, 50), count } : null;
  }
  if (kind === "locate") {
    const { el, count } = find(arg);
    if (!el) return null;
    el.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
    return { el: name(el), text: txt(el).slice(0, 50), count, covered: covered(el), ...center(el) };
  }
  if (kind === "scroll") {
    const box = arg.in ? document.querySelector(arg.in) : null;
    if (arg.in && !box) return false;
    (box || window).scrollBy(0, arg.by);
    return true;
  }
  if (kind === "range") {
    const { el } = find(arg);
    if (!el) return null;
    el.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
    const r = document.createRange();
    r.selectNodeContents(el);
    const rects = [...r.getClientRects()].filter((x) => x.width > 0);
    if (!rects.length) return null;
    const a = rects[0], b = rects[rects.length - 1];
    return { el: name(el), x1: a.left + 1, y1: a.top + a.height / 2, x2: b.right - 1, y2: b.top + b.height / 2 };
  }
  if (kind === "clear") {
    const a = document.activeElement;
    if (a && "value" in a) { a.value = ""; a.dispatchEvent(new Event("input", { bubbles: true })); } else document.execCommand("selectAll");
    return true;
  }
  return null;
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    const pending = new Map(), listeners = new Map();
    let id = 0;
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending.has(d.id)) {
        const p = pending.get(d.id);
        pending.delete(d.id);
        if (d.error) p.reject(new Error(d.error.message)); else p.resolve(d.result);
      } else if (d.method) for (const fn of listeners.get(d.method) || []) fn(d.params);
    };
    ws.onerror = () => reject(new Error("нет связи с Chrome"));
    ws.onopen = () => resolve({
      // У каждого запроса свой предел: переадресация посреди запроса иначе вешает скрипт навсегда.
      send(method, params = {}) {
        return new Promise((res, rej) => {
          const i = ++id;
          pending.set(i, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id: i, method, params }));
          setTimeout(() => { if (pending.has(i)) { pending.delete(i); rej(new Error(`${method}: нет ответа 20 с`)); } }, 20000);
        });
      },
      on(method, fn) { if (!listeners.has(method)) listeners.set(method, []); listeners.get(method).push(fn); },
      once(method, ms) {
        return new Promise((res) => {
          let done = false;
          this.on(method, (p) => { if (!done) { done = true; res(p); } });
          setTimeout(() => { if (!done) { done = true; res(null); } }, ms);
        });
      },
      close() { try { ws.close(); } catch (e) { /* уже закрыт */ } },
    });
  });
}

// Порт выбирает сам Chrome и пишет его в профиль: случайный порт мог оказаться портом чужого Chrome.
async function launch(headless, profile) {
  const flags = ["--remote-debugging-port=0", `--user-data-dir=${profile}`, "--no-first-run",
    "--no-default-browser-check", "--lang=ru-RU", "--window-size=1440,900"];
  if (headless) flags.unshift("--headless=new", "--disable-gpu", "--hide-scrollbars");
  const proc = spawn(chromePath(), [...flags, "about:blank"], { stdio: "ignore", detached: true });
  proc.once("error", () => {});
  try {
    let page = null, version = null;
    for (let i = 0; i < 75 && !page; i++) {
      await sleep(200);
      try {
        const port = fs.readFileSync(path.join(profile, "DevToolsActivePort"), "utf8").split("\n")[0].trim();
        version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
        page = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page");
      } catch (e) { /* Chrome ещё поднимается */ }
    }
    if (!page) throw new Error("Chrome не запустился");
    const cdp = await connect(page.webSocketDebuggerUrl);
    return { proc, cdp, userAgent: String(version["User-Agent"] || "").replace("HeadlessChrome", "Chrome") };
  } catch (e) {
    try { process.kill(-proc.pid, "SIGKILL"); } catch (e2) { /* не запустился вовсе */ }
    fs.rmSync(profile, { recursive: true, force: true });
    throw e;
  }
}

// Вход по auth.json: POST логина, cookie ответа — в браузер, на адрес приложения.
// Форма входа отвечает редиректом с cookie — его не проходим, иначе cookie теряется.
async function login(cdp, auth, origin) {
  if (!auth.login) return;
  const { form, json } = auth.login;
  const r = await fetch(origin + auth.login.path, form
    ? { method: "POST", body: new URLSearchParams(form), redirect: "manual" }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(json || {}) });
  if (r.status >= 400) throw new Error(`вход не удался: ${r.status}`);
  for (const c of r.headers.getSetCookie()) {
    const nv = c.split(";")[0], i = nv.indexOf("=");
    const name = nv.slice(0, i).trim(), value = nv.slice(i + 1).trim();
    if (name && value) await cdp.send("Network.setCookie", { name, value, url: origin, httpOnly: true });
  }
}

function dedupe(list) {
  const seen = new Map();
  for (const x of list) seen.set(x, (seen.get(x) || 0) + 1);
  return [...seen].map(([x, n]) => (n > 1 ? `${x}  ×${n}` : x));
}

async function main() {
  const { pos, opt } = parseArgs(process.argv.slice(2));
  const [cmd, target] = pos;
  if (!["shot", "run", "open"].includes(cmd) || !target) { console.error(USAGE); process.exit(1); }
  const auth = opt.auth ? JSON.parse(fs.readFileSync(opt.auth, "utf8")) : {};
  const scenario = cmd === "run" ? JSON.parse(fs.readFileSync(target, "utf8")) : {
    start: target,
    viewports: opt.both ? ["desktop", "mobile"] : [opt.mobile ? "mobile" : "desktop"],
    steps: [{ shot: opt.name || "page", frames: +(opt.frames || 3) }],
  };
  const abs = (u) => {
    if (/^https?:/.test(u)) return u;
    if (!auth.base) throw new Error(`относительный адрес «${u}» без base в auth.json`);
    return new URL(u, auth.base).href;
  };
  const startUrl = abs(scenario.start || "/");
  const origin = new URL(startUrl).origin;

  if (cmd === "open") {
    // Окно для человека: свой временный профиль, вход по auth.json, скрипт уходит — окно остаётся.
    const profile = fs.mkdtempSync(path.join(os.tmpdir(), "look-open-"));
    const { proc, cdp } = await launch(false, profile);
    await login(cdp, auth, origin);
    await cdp.send("Page.navigate", { url: startUrl });
    await sleep(1500);
    cdp.close();
    proc.unref();
    console.log(`Окно Chrome открыто: ${startUrl}`);
    process.exit(0);
  }

  const out = path.resolve(opt.out || path.join(os.tmpdir(), `look-${Date.now()}`));
  fs.mkdirSync(out, { recursive: true });
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "look-"));
  const { proc, cdp, userAgent } = await launch(true, profile);
  const lines = [], steps = [];
  const ev = { errors: [], console: [], failed: [], blocked: [], dialogs: [] };
  let label = "", vp = VIEWPORTS.desktop;

  const finish = (code) => {
    try { process.kill(-proc.pid, "SIGKILL"); } catch (e) { /* уже закрыт */ }
    fs.rmSync(profile, { recursive: true, force: true });
    const sect = (title, arr) => {
      lines.push("", `${title}: ${arr.length ? "" : "нет"}`);
      for (const x of dedupe(arr).slice(0, 40)) lines.push(`  ${x}`);
    };
    sect("Ошибки страницы", ev.errors);
    sect("Консоль (ошибки и предупреждения)", ev.console);
    sect("Упавшие запросы", ev.failed);
    if (opt.readonly) sect("Заблокировано (режим «только смотреть»)", ev.blocked);
    sect("Диалоги (подтверждены автоматически)", ev.dialogs);
    fs.writeFileSync(path.join(out, "report.txt"), lines.join("\n") + "\n");
    fs.writeFileSync(path.join(out, "report.json"), JSON.stringify({ start: startUrl, steps, ...ev }, null, 2));
    console.log(`Готово: ${out}/report.txt\n` + fs.readdirSync(out).filter((f) => f.endsWith(".png")).map((f) => `  ${out}/${f}`).join("\n"));
    process.exit(code);
  };
  setTimeout(() => { lines.push(`Сторож: прогон дольше ${opt.timeout || 180} с — остановлен`); finish(3); },
    (+opt.timeout || 180) * 1000);
  try {
    await run();
    finish(0);
  } catch (e) {
    lines.push(`Прогон прерван: ${e.message}`);
    finish(1);
  }

  async function run() {
    const expr = async (expression) => {
      const r = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(String(r.exceptionDetails.exception?.description || r.exceptionDetails.text).split("\n")[0]);
      return r.result ? r.result.value : null;
    };
    const evalJs = (kind, arg) => expr(`(${inPage})(${JSON.stringify(kind)}, ${JSON.stringify(arg ?? null)})`);

    // Что упало, что ругалось — привязываем к шагу, на котором случилось.
    const reqs = new Map(), inflight = new Set();
    // Точное сравнение адреса: по началу строки прошли бы https://наш-сайт@чужой.com и соседний порт.
    const sameOrigin = (u) => { try { return new URL(u).origin === origin; } catch (e) { return false; } };
    const short = (u) => sameOrigin(u) ? u.slice(origin.length) : u.slice(0, 120);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Log.enable");
    await cdp.send("Network.enable");
    cdp.on("Runtime.consoleAPICalled", (e) => {
      if (e.type !== "error" && e.type !== "warning") return;
      ev.console.push(`[${label}] ${e.type}: ${e.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 240)}`);
    });
    cdp.on("Runtime.exceptionThrown", (e) => {
      const d = e.exceptionDetails || {};
      ev.errors.push(`[${label}] ${String((d.exception && d.exception.description) || d.text || "").split("\n")[0].slice(0, 240)}`);
    });
    cdp.on("Log.entryAdded", (e) => {
      if (e.entry.level === "error" && e.entry.source !== "network") ev.console.push(`[${label}] ${e.entry.text.slice(0, 240)}`);
    });
    cdp.on("Network.requestWillBeSent", (e) => {
      if (e.request.url.startsWith("data:")) return;
      reqs.set(e.requestId, { method: e.request.method, url: e.request.url });
      if (e.type !== "EventSource" && e.type !== "WebSocket") inflight.add(e.requestId);
    });
    cdp.on("Network.responseReceived", (e) => {
      const r = reqs.get(e.requestId) || { method: "GET", url: e.response.url };
      if (e.response.status >= 400 && !/\/favicon\.ico$/.test(r.url)) ev.failed.push(`[${label}] ${e.response.status} ${r.method} ${short(r.url)}`);
    });
    cdp.on("Network.loadingFinished", (e) => inflight.delete(e.requestId));
    cdp.on("Network.loadingFailed", (e) => {
      inflight.delete(e.requestId);
      const r = reqs.get(e.requestId);
      if (r && !e.canceled && e.errorText !== "net::ERR_BLOCKED_BY_CLIENT") ev.failed.push(`[${label}] ${e.errorText} ${r.method} ${short(r.url)}`);
    });
    cdp.on("Page.javascriptDialogOpening", (e) => {
      ev.dialogs.push(`[${label}] ${e.type} «${e.message}»`);
      cdp.send("Page.handleJavaScriptDialog", { accept: true, promptText: e.defaultPrompt || "" }).catch(() => {});
    });

    // Ключ — только своему сайту; «только смотреть» — любая запись блокируется, откуда бы ни шла.
    if (auth.bearer || opt.readonly) {
      await cdp.send("Fetch.enable", { patterns: [{ urlPattern: "*", requestStage: "Request" }] });
      cdp.on("Fetch.requestPaused", (e) => {
        if (opt.readonly && !["GET", "HEAD", "OPTIONS"].includes(e.request.method)) {
          ev.blocked.push(`[${label}] ${e.request.method} ${short(e.request.url)}`);
          cdp.send("Fetch.failRequest", { requestId: e.requestId, errorReason: "BlockedByClient" }).catch(() => {});
        } else if (auth.bearer && sameOrigin(e.request.url)) {
          const headers = Object.entries(e.request.headers).map(([n, value]) => ({ name: n, value }));
          headers.push({ name: "Authorization", value: `Bearer ${auth.bearer}` });
          cdp.send("Fetch.continueRequest", { requestId: e.requestId, headers }).catch(() => {});
        } else cdp.send("Fetch.continueRequest", { requestId: e.requestId }).catch(() => {});
      });
    }
    await login(cdp, auth, origin);

    // Готово — когда документ загружен, сеть затихла на полсекунды и шрифты на месте.
    const settle = async (maxMs = 8000) => {
      const t0 = Date.now();
      while (Date.now() - t0 < maxMs && (await expr("document.readyState")) !== "complete") await sleep(100);
      let quiet = Date.now();
      while (Date.now() - t0 < maxMs) {
        if (inflight.size) quiet = Date.now(); else if (Date.now() - quiet > 500) break;
        await sleep(100);
      }
      await expr("document.fonts ? document.fonts.ready.then(() => true) : true");
      await sleep(250);
    };
    const go = async (url) => {
      const loaded = cdp.once("Page.loadEventFired", 15000);
      const nav = await cdp.send("Page.navigate", { url });
      if (nav.errorText) throw new Error(`страница не открылась: ${nav.errorText}`);
      await loaded;
      await settle();
    };
    const clickAt = async (x, y) => {
      if (vp.mobile) {
        await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
        await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      } else {
        await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
        await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
        await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
      }
    };
    // Один кадр — то, что человек видит сейчас; несколько — обзор страницы сверху вниз, прокрутка потом на место.
    const shoot = async (vpName, n, shotName, frames) => {
      const o = await evalJs("outline");
      const total = Math.max(1, Math.ceil((o.pageHeight - 80) / (vp.height - 80)));
      const count = Math.min(Math.max(1, frames), total);
      const y0 = await expr("scrollY");
      const files = [];
      for (let i = 0; i < count; i++) {
        if (count > 1) { await expr(`window.scrollTo(0, ${i * (vp.height - 80)})`); await sleep(200); }
        const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
        const file = `${vpName}-${n}-${shotName}${count > 1 ? `-${i + 1}` : ""}.png`;
        fs.writeFileSync(path.join(out, file), Buffer.from(data, "base64"));
        files.push(file);
      }
      if (count > 1) await expr(`window.scrollTo(0, ${y0})`);
      const res = [count > 1 ? `кадры → ${files.join(", ")}; страница ${o.pageHeight} px — сверху вниз ${count} экрана из ${total}`
        : `кадр → ${files[0]}; текущий экран${y0 ? ` (прокручено на ${Math.round(y0)} px)` : ""}, страница ${o.pageHeight} px ≈ ${total} экр.`];
      if (o.heads.length) res.push(`Заголовки: ${o.heads.join(" · ")}`);
      if (o.scrollers.length) res.push(`Прокручивается внутри блока: ${o.scrollers.join(", ")}`);
      res.push(`Можно нажать (${o.items.length}): ` + o.items.map((it) =>
        `[${it.el}] «${it.text}»${it.disabled ? " (неактивно)" : ""}${it.covered ? ` (перекрыто: ${it.covered})` : ""}`).join(" · "));
      return res;
    };

    const doStep = async (s, vpName, n) => {
      if (s.shot !== undefined) return { ok: true, info: await shoot(vpName, n, String(s.shot || "shot"), +(s.frames || 1)) };
      if (s.go) { await go(abs(s.go)); return { ok: true, info: [`открыта ${s.go}`] }; }
      if (s.click || s.type) {
        const q = s.click || s.type;
        const loc = await evalJs("locate", q);
        if (!loc) return { ok: false, info: [`не нашёл на странице: ${q}`] };
        await sleep(120);
        await clickAt(loc.x, loc.y);
        const info = [`${loc.el} «${loc.text}»${loc.count > 1 ? `, похожих ещё ${loc.count - 1}` : ""}${loc.covered ? ` — ПЕРЕКРЫТ элементом ${loc.covered}` : ""}`];
        if (s.type) {
          await sleep(120);
          if (s.clear) await evalJs("clear");
          await cdp.send("Input.insertText", { text: String(s.text || "") });
          info.push(`введено: «${String(s.text || "").slice(0, 60)}»`);
        }
        await sleep(300);
        await settle(6000);
        return { ok: true, info };
      }
      if (s.select) {
        // Выделение мышью, как у человека: нажал в начале текста, отпустил в конце.
        const r = await evalJs("range", s.select);
        if (!r) return { ok: false, info: [`нет текста для выделения: ${s.select}`] };
        await sleep(120);
        await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: r.x1, y: r.y1 });
        await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: r.x1, y: r.y1, button: "left", clickCount: 1 });
        await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: r.x2, y: r.y2, button: "left", buttons: 1 });
        await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: r.x2, y: r.y2, button: "left", clickCount: 1 });
        await sleep(300);
        return { ok: true, info: [`выделено в ${r.el}: «${String(await expr("getSelection().toString()")).slice(0, 60)}»`] };
      }
      if (s.press) {
        const parts = String(s.press).split("+"), k = parts.pop();
        const modifiers = parts.reduce((m, p) => m | (MODS[p] || 0), 0);
        const [code, text] = KEYS[k] || [k.length === 1 ? k.toUpperCase().charCodeAt(0) : 0, k.length === 1 ? k : ""];
        const key = { key: k === "Space" ? " " : k, code: KEYS[k] ? k : `Key${k.toUpperCase()}`, windowsVirtualKeyCode: code,
          nativeVirtualKeyCode: code, modifiers };
        await cdp.send("Input.dispatchKeyEvent", { type: text && !modifiers ? "keyDown" : "rawKeyDown", ...key, text: modifiers ? "" : text });
        await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", ...key });
        await sleep(300);
        await settle(6000);
        return { ok: true, info: [`нажата ${s.press}`] };
      }
      if (s.wait !== undefined) {
        if (typeof s.wait === "number") { await sleep(s.wait); return { ok: true, info: [`пауза ${s.wait} мс`] }; }
        const t0 = Date.now(), limit = +(s.timeout || 5000);
        while (Date.now() - t0 < limit) {
          const f = await evalJs("find", s.wait);
          if (f) return { ok: true, info: [`появилось: ${f.el} «${f.text}»`] };
          await sleep(150);
        }
        return { ok: false, info: [`не дождался за ${limit / 1000} с: ${s.wait}`] };
      }
      if (s.scroll !== undefined) {
        const ok = await evalJs("scroll", { by: +s.scroll, in: s.in || "" });
        await sleep(300);
        return ok ? { ok: true, info: [`прокрутка на ${s.scroll}${s.in ? ` внутри ${s.in}` : ""}`] } : { ok: false, info: [`нет блока ${s.in}`] };
      }
      return { ok: false, info: [`непонятный шаг: ${JSON.stringify(s)}`] };
    };

    lines.push(`Взгляд — ${new Date().toLocaleString("ru-RU")}; старт ${startUrl}${opt.readonly ? " (только смотреть)" : ""}`);
    for (const vpName of scenario.viewports || ["desktop", "mobile"]) {
      vp = VIEWPORTS[vpName];
      if (!vp) { lines.push(`Неизвестный размер экрана: ${vpName}`); continue; }
      label = `${vpName} 00`;
      await cdp.send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: vp.deviceScaleFactor, mobile: vp.mobile });
      await cdp.send("Emulation.setTouchEmulationEnabled", vp.mobile ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
      await cdp.send("Network.setUserAgentOverride", { userAgent: vp.mobile ? MOBILE_UA : userAgent, acceptLanguage: "ru-RU,ru;q=0.9" });
      lines.push("", `${vpName} ${vp.width}×${vp.height}`);
      try { await go(startUrl); } catch (e) { lines.push(`  не открылась стартовая страница: ${e.message}`); continue; }
      const list = scenario.steps || [];
      for (let i = 0; i < list.length; i++) {
        const n = String(i + 1).padStart(2, "0");
        label = `${vpName} ${n}`;
        let r;
        try { r = await doStep(list[i], vpName, n); } catch (e) { r = { ok: false, info: [`ошибка шага: ${e.message}`] }; }
        const head = Object.keys(list[i]).filter((k) => !["text", "timeout", "frames", "clear", "in"].includes(k))
          .map((k) => `${k} ${JSON.stringify(list[i][k])}`).join(" ");
        lines.push(`  ${n} ${head} — ${r.ok ? "ок" : "НЕ УДАЛОСЬ"}`, ...r.info.map((x) => `     ${x}`));
        steps.push({ viewport: vpName, n, step: list[i], ok: r.ok, info: r.info });
        if (!r.ok) {
          lines.push(...(await shoot(vpName, n, "fail", 1)).map((x) => `     ${x}`));
          break;
        }
      }
    }
  }
}

main().catch((e) => { console.error(`look.js: ${e.message}`); process.exit(1); });
