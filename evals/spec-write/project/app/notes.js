// Страница заметок: список, добавление, удаление.
const list = document.getElementById("list");
const empty = document.getElementById("empty");
let notes = [];

async function load() {
  notes = await (await fetch("/api/notes")).json();
  render();
}

function render() {
  list.innerHTML = "";
  empty.hidden = notes.length > 0;
  for (const n of notes) {
    const li = document.createElement("li");
    const box = document.createElement("div");
    const title = document.createElement("b");
    title.textContent = n.title;
    const text = document.createElement("span");
    text.textContent = n.text || n.created;
    box.append(title, text);
    const del = document.createElement("button");
    del.textContent = "Удалить";
    del.onclick = async () => {
      if (!confirm("Удалить заметку? Вернуть её будет нельзя.")) return;
      await fetch("/api/notes/" + n.id, { method: "DELETE" });
      load();
    };
    li.append(box, del);
    list.append(li);
  }
}

document.getElementById("add").onsubmit = async e => {
  e.preventDefault();
  const input = document.getElementById("title");
  if (!input.value.trim()) return;
  await fetch("/api/notes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: input.value }) });
  input.value = "";
  load();
};

load();
