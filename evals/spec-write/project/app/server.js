// Заметки: крошечный сервер учебного проекта. Запуск: node app/server.js [порт]
const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.argv[2] || process.env.PORT || 5180);
let nextId = 5;
let notes = [
  { id: 1, owner: "anna", title: "Список покупок", text: "Молоко, хлеб, сыр", created: "2026-11-01" },
  { id: 2, owner: "anna", title: "Идея для подарка", text: "Книга о садах", created: "2026-11-05" },
  { id: 3, owner: "anna", title: "Звонок мастеру", text: "Перезвонить во вторник после обеда", created: "2026-11-09" },
  { id: 4, owner: "boris", title: "Пароль от домофона", text: "Спросить у соседа", created: "2026-11-10" },
];

const send = (res, code, body, type = "application/json; charset=utf-8") => {
  res.writeHead(code, { "Content-Type": type });
  res.end(body);
};
const readBody = req => new Promise(resolve => {
  let raw = "";
  req.on("data", c => (raw += c));
  req.on("end", () => { try { resolve(JSON.parse(raw || "{}")); } catch { resolve({}); } });
});
const PAGES = { "/": "notes.html", "/notes.html": "notes.html", "/notes.js": "notes.js" };

http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  const user = String(req.headers["x-user"] || "anna");
  if (req.method === "GET" && url.pathname === "/api/notes") {
    return send(res, 200, JSON.stringify(notes.filter(n => n.owner === user)));
  }
  if (req.method === "POST" && url.pathname === "/api/notes") {
    const body = await readBody(req);
    const title = String(body.title || "").trim().slice(0, 200);
    if (!title) return send(res, 400, JSON.stringify({ error: "Нужно название" }));
    const note = { id: nextId++, owner: user, title, text: String(body.text || "").slice(0, 5000), created: new Date().toISOString().slice(0, 10) };
    notes.push(note);
    return send(res, 200, JSON.stringify(note));
  }
  if (req.method === "DELETE" && url.pathname.startsWith("/api/notes/")) {
    const id = Number(url.pathname.split("/").pop());
    notes = notes.filter(n => !(n.id === id && n.owner === user)); // удаляет сразу и навсегда
    return send(res, 200, JSON.stringify({ ok: true }));
  }
  const page = PAGES[url.pathname];
  if (req.method === "GET" && page) {
    const type = page.endsWith(".js") ? "text/javascript; charset=utf-8" : "text/html; charset=utf-8";
    return send(res, 200, fs.readFileSync(path.join(__dirname, page)), type);
  }
  send(res, 404, JSON.stringify({ error: "Нет такой страницы" }));
}).listen(PORT, "127.0.0.1", () => console.log("Заметки: http://127.0.0.1:" + PORT + "/"));
