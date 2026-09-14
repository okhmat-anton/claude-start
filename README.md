# claude-start — /start и общая база знаний агентов

- `project_start.md` — команда `/start`: интервью, генерация системы самосовершенствования проекта, подключение базы знаний.
- `knowledge/` — база знаний, общая для всех проектов. Формат единиц — `knowledge/FORMAT.md`; оглавление `INDEX.md` генерируется.
  - `lessons/` — уроки «триггер → действие» (одна ситуация = одна единица, ≤30 строк прозы, обязательные триггеры);
  - `stacks/` — справочники по стекам; `skills/` — переносимые скиллы (`scope: global` ставятся в `~/.claude/skills`);
  - `usage.json` — показы и применения уроков (обратная связь для уборки).
- `tools/knowledge.py` — lint / index / match / hit / new / gc / stats. `tools/hook.py` — глобальные хуки Claude Code.
- `tools/install.sh` — подключает хуки и глобальные скиллы к `~/.claude` (идемпотентно). `make install`.
- `evals/cases.json` + `tools/evals.py` — регрессия триггеров (офлайн) и поведения агента (`--live`, платно).

## Как знания попадают к агенту
1. `UserPromptSubmit` — хук подбирает до 3 уроков по ключам промта и вкладывает их в контекст.
2. `PreToolUse(Bash)` — до 2 уроков по шаблону команды (`docker compose up`, `ffmpeg … xfade`, `ssh … psql`).
3. `SessionStart` — размер CLAUDE.md, неразобранные поправки владельца, застрявшие кандидаты.
4. `Stop` — если правок ≥5, а retro не было, просит прогнать retro (один раз за сессию).

## Как знания растут
retro в проекте → `knowledge.py new` (кандидат, `seen_in: [проект]`) → второй проект добавляет себя в `seen_in` →
`status: mature`. Применил подсказку → `knowledge.py hit <name>`. Раз в месяц `knowledge-gc` чистит по `usage.json`.

```
make lint    # формат единиц
make index   # пересобрать INDEX.md
make test    # lint + index --check + евалы триггеров
make gc      # отчёт уборки
```
