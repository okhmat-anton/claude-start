---
name: architecture-mvc
description: MVC в духе Yii2 advanced — роут = файл + функция, async-экшены index/view/…, роут в docstring, логика в экшене, слои public/admin/console в одном app
stack: [python, fastapi, vue, nuxt, node]
triggers:
  keywords: [контроллер, экшен, роут, эндпоинт, endpoint, новый проект, структур, куда полож, mvc, yii, каркас проекта, админк]
  commands: []
  errors: []
  paths: ['app/controllers/*', 'controllers/*', 'app/commands/*', 'commands/*']
---
# Архитектурный стандарт: MVC в духе Yii2 advanced

Действует на проекты, созданные после 2026-09. Существующие проекты живут по своим
правилам — миграция только по явной просьбе владельца.

Зачем: для любой задачи заранее известно, какой файл открыть и какую функцию искать.
Читаемость важнее краткости: упрощение, после которого код труднее прочитать, — не упрощение.

## Три правила, из которых следует всё

1. **Роут = файл + функция.** `GET /order/history` → `app/controllers/order.py` →
   `async def history()`. Адрес кода известен заранее, без грепа по проекту.
2. **Логика задачи — в экшене.** Открыл функцию — видишь задачу целиком сверху вниз.
   Вынос в models/ или общий модуль — только по «правилу двух»: код понадобился второму месту.
3. **Первая строка docstring — роут и назначение.** `"""GET /order/history — история
   заказов покупателя."""` В FastAPI она же видна в /docs (OpenAPI summary).

## Backend (Python + FastAPI)

Слои Yii2 advanced внутри одного приложения:

```
app/
  controllers/            # HTTP-слой (= frontend): файл = контроллер
    __init__.py           # собирает роутеры в api_router — единственная точка подключения
    site.py               # /, /site/about, /site/contact
    order.py              # /order, /order/{id}, /order/history
    admin/                # (= backend): префикс /admin, Depends(get_current_admin) на роутере
      orders.py           # /admin/orders…
  commands/               # (= console): CLI-скрипты, запуск python -m app.commands.<имя>
  models/                 # (= common): SQLAlchemy/Pydantic-модели, общие для всех слоёв
  core/                   # config (pydantic-settings), db, auth-зависимости
  views/                  # только при SSR: Jinja2, views/<controller>/<action>.html
```

- Экшены — **всегда `async def`**.
- Стандартные имена экшенов (как в Yii2), кастомные — по последнему сегменту роута:

| Роут | Функция |
|---|---|
| `GET /order` | `index()` — список |
| `GET /order/{id}` | `view(id)` — карточка |
| `POST /order` | `create()` |
| `PUT/PATCH /order/{id}` | `update(id)` |
| `DELETE /order/{id}` | `delete(id)` |
| `GET /order/history` | `history()` |

- Один контроллер — один файл со ВСЕМИ его экшенами; не дробить, пока файл < ~700 строк.

```python
# app/controllers/order.py — заказы: список, карточка, история
from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.order import Order

router = APIRouter(prefix="/order", tags=["order"])


@router.get("")
async def index(user=Depends(get_current_user)):
    """GET /order — список заказов текущего пользователя."""
    ...  # вся логика здесь, сверху вниз; хелперы — только по правилу двух


@router.get("/history")
async def history(user=Depends(get_current_user)):
    """GET /order/history — история заказов с суммами по месяцам."""
    ...
```

(`@router.get("/history")` объявляй ДО `"/{order_id}"`, иначе FastAPI примет history за id.)

## Frontend (JS)

- **Nuxt** — file-routing уже даёт этот принцип: URL = путь файла
  (`pages/article/[id].vue` = `/article/<id>`). Обязательная шапка в каждом
  page-компоненте: `<!-- /article/[id] — страница статьи -->`.
- **Vue SPA** — `src/pages/<Controller>/<Action>.vue` (например `pages/Order/Index.vue`),
  роутер — один явный `router/index.js`, имя маршрута `order-index`. Логика страницы —
  в её `<script setup>`; composables — по правилу двух.
- **Node/Express** (если backend на JS) — те же правила: `routes/order.js`,
  `async function history()`, над ней `// GET /order/history — что делает`.

## Console (commands/)

Каждый CLI-сценарий — отдельный файл `app/commands/<имя>.py` с docstring-шапкой:
как запускать, что делает, какие аргументы. Запуск: `python -m app.commands.<имя>`.
Применимо и к проектам без HTTP-слоя (воркеры, генераторы, разовые миграции данных).

## Пороги дробления и слияния (ими же руководствуется упроститель)

- Вынос кода из экшена/файла: «правило двух» ИЛИ файл > ~700 строк. Резать по смысловым
  границам (`order.py` → `order.py` + `order_export.py`), а не в `utils.py`/`helpers.py`-свалку.
- Файл < ~40 строк, одна функция, один потребитель — кандидат на слияние с потребителем.
- Запрещено без нужды: слой-прослойка ради «чистоты», обёртка над stdlib, «менеджер»/
  «фабрика» с единственной реализацией, дробление на сотни файлов.
