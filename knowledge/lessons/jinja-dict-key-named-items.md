---
name: jinja-dict-key-named-items
description: Jinja: ключ словаря items/keys/values в шаблоне отдаёт метод, а не значение — читать через d['items'] или переименовать
stack: [python]
status: candidate
created: 2026-09-30
seen_in: [video-blade-2]
triggers:
  keywords: [jinja, built-in method, ключ items, словарь в шаблоне, dict.items]
  commands: []
  errors: ["built-in method \w+ of dict"]
  paths: ["templates/**/*.html", "*.j2", "*.jinja*"]
---
# Jinja: ключ словаря items/keys/values в шаблоне отдаёт метод, а не значение — читать через d['items'] или переименовать

Контекст: в контекст шаблона ушёл словарь с ключом `items`; `{{ plan.items }}` отрисовал «<built-in method items of
dict object…>» — для `a.b` Jinja сначала пробует атрибут, и метод словаря побеждает ключ.

Урок:
- ключ, совпадающий с методом словаря (items, keys, values, get, pop, update, copy), читай через `d['items']`
  или переименуй ключ ещё в Python;
- признак: в разметке или тесте всплыло «built-in method» — это оно, а не пустые данные;
- цена: страница не падает, а тихо показывает мусор — заметит только человек на кадре.
