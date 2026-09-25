// Reddit через настоящий Chrome без окна (новый интерфейс прячет текст в теневом DOM —
// берём атрибуты компонентов shreddit-post / shreddit-comment).
//   node reddit.js list <url> <out.json>        — посты со страницы сабреддита / поиска
//   node reddit.js thread <url> <out.json>      — пост целиком + комментарии
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const [cmd, url, out] = process.argv.slice(2);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9400 + Math.floor(Math.random() * 400);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), "rd-"));
const ch = spawn(CHROME, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`,
  "--window-size=1400,3000", "--lang=en-US", "about:blank"], { stdio: "ignore", detached: true });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const done = (code) => { try { process.kill(-ch.pid, "SIGKILL"); } catch (e) {} fs.rmSync(prof, { recursive: true, force: true }); process.exit(code); };
// Сторож: страница может переадресоваться посреди запроса, и ответ не придёт никогда.
setTimeout(() => { console.error("watchdog: 150s"); done(3); }, 150000);

const LIST = `Array.from(document.querySelectorAll("shreddit-post")).map(p => ({
  title: p.getAttribute("post-title"), score: +p.getAttribute("score") || 0,
  comments: +p.getAttribute("comment-count") || 0, link: p.getAttribute("permalink"),
  sub: p.getAttribute("subreddit-prefixed-name"), created: p.getAttribute("created-timestamp"),
  type: p.getAttribute("post-type")
}))`;
const THREAD = `(() => {
  const post = document.querySelector("shreddit-post");
  const body = post ? (post.querySelector('[slot="text-body"]') || post.querySelector('[slot="post-media-container"]') || post) : null;
  const comments = Array.from(document.querySelectorAll("shreddit-comment")).map(c => {
    const slot = c.querySelector('[slot="comment"]');
    return { author: c.getAttribute("author"), score: +c.getAttribute("score") || 0, depth: +c.getAttribute("depth") || 0,
             text: (slot ? slot.innerText : "").trim() };
  }).filter(c => c.text);
  return {
    title: post ? post.getAttribute("post-title") : document.title, score: post ? +post.getAttribute("score") : null,
    commentCount: post ? +post.getAttribute("comment-count") : null, sub: post ? post.getAttribute("subreddit-prefixed-name") : null,
    created: post ? post.getAttribute("created-timestamp") : null, body: body ? body.innerText.trim() : "", comments
  };
})()`;

(async () => {
  let targets;
  for (let i = 0; i < 50; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch (e) { await sleep(200); } }
  const page = targets.find(t => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = {};
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; } };
  const send = (method, params = {}) => new Promise((resolve) => {
    const i = ++id; pending[i] = resolve; ws.send(JSON.stringify({ id: i, method, params }));
    setTimeout(() => { if (pending[i]) { delete pending[i]; resolve({ timeout: true }); } }, 20000);
  });
  const evalJs = async (expression) => { const r = await send("Runtime.evaluate", { expression, returnByValue: true }); return r.result && r.result.result ? r.result.result.value : null; };
  await send("Network.enable");
  await send("Network.setUserAgentOverride", { userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36", acceptLanguage: "en-US,en;q=0.9" });
  await send("Page.enable");
  await send("Page.navigate", { url });
  // Проверка «js_challenge» переадресует страницу — ждём, пока появятся компоненты.
  let data = null;
  const probe = cmd === "search" ? 'document.querySelectorAll(\'a[href*="/comments/"]\').length' : 'document.querySelectorAll("shreddit-post").length';
  for (let i = 0; i < 30; i++) {
    await sleep(1000);
    const n = await evalJs(probe);
    if (n > 0) break;
  }
  if (cmd === "search") {
    // Страница поиска: карточки без компонентов — берём ссылки на обсуждения и цифры из текста карточки.
    for (let i = 0; i < 4; i++) { await evalJs("window.scrollTo(0, document.body.scrollHeight)"); await sleep(1500); }
    data = await evalJs(`(() => {
      const seen = new Map();
      for (const a of document.querySelectorAll('a[href*="/comments/"]')) {
        const href = a.getAttribute("href").split("?")[0].replace(/^https?:\\/\\/www\\.reddit\\.com/, "");
        const text = (a.innerText || "").trim();
        if (!text || text.length < 12 || !/\\/comments\\/[a-z0-9]+\\//.test(href)) continue;
        let card = a; for (let k = 0; k < 7 && card.parentElement; k++) { card = card.parentElement; if (card.getAttribute("data-testid") === "search-post-unit" || card.tagName === "ARTICLE") break; }
        const t = card.innerText || "";
        const votes = +((t.match(/(\\d[\\d,.]*[kK]?)\\s+(votes?|upvotes?)/) || [])[1] || "").replace(/,/g, "").replace(/k$/i, "000") || 0;
        const comments = +((t.match(/(\\d[\\d,.]*[kK]?)\\s+comments?/) || [])[1] || "").replace(/,/g, "").replace(/k$/i, "000") || 0;
        const key = href.replace(/\\/$/, "");
        if (!seen.has(key) || seen.get(key).title.length < text.length) seen.set(key, { title: text, link: key + "/", score: votes, comments });
      }
      return Array.from(seen.values());
    })()`);
  } else if (cmd === "list") {
    // Подгрузка ленты при прокрутке — несколько прокруток, чтобы набрать больше постов.
    for (let i = 0; i < 6; i++) { await evalJs("window.scrollTo(0, document.body.scrollHeight)"); await sleep(1500); }
    data = await evalJs(LIST);
  } else {
    // Догрузить комментарии: прокрутка и кнопки «ещё…», пока число растёт (потолок — 120).
    let last = -1;
    for (let i = 0; i < 14; i++) {
      await evalJs(`document.querySelectorAll("button, summary").forEach(b => { const t = (b.innerText || "").trim(); if (/^(view )?(\\d+ )?more (comments|repl)/i.test(t) || /^load more/i.test(t)) b.click(); })`);
      await evalJs("window.scrollTo(0, document.body.scrollHeight)");
      await sleep(1800);
      const n = await evalJs('document.querySelectorAll("shreddit-comment").length');
      if (n >= 120 || n === last) { if (n === last && i > 3) break; }
      last = n;
    }
    data = await evalJs(THREAD);
  }
  fs.writeFileSync(out, JSON.stringify(data, null, 1));
  const summary = Array.isArray(data) ? { posts: data.length } : { title: data && data.title, bodyChars: data && data.body.length, comments: data && data.comments.length };
  console.log(JSON.stringify({ url: await evalJs("location.href"), ...summary }));
  done(0);
})().catch(e => { console.error(e); done(1); });
