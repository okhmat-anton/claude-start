# INDEX — оглавление базы знаний

Одна строка на единицу знания: что это, для какого стека, из какого проекта пришло.

Формат: `- [путь] — краткое описание (стек; from <проект>)`

- [skills/viewer-reviewer/SKILL.md] — ревью контента «глазами наивного зрителя» с подтверждением цели у автора (контент-проекты: видео, статьи, лендинги; from work-video-production)
- [lessons/api-discovery.md] — порядок поиска недокументированных эндпоинтов/полей REST API: вторичные доки → журнал уроков → живой GET → пробная запись с echo (любой проект на внешнем REST API; from work-video-production)
- [lessons/agent-shell-state.md] — PATH/cwd не персистятся между Bash-вызовами агента: export PATH + абсолютные пути, иначе файлы падают в корень репо (любой агентный CLI-харнесс; from work-video-production)
- [skills/standard-stack/SKILL.md] — единый стандарт стека, команд (make run/test/lint/build/update), именования, git и деплоя для всех проектов; вопросы-стандарты в /start больше не задаются (python+fastapi, vue/js, postgres, docker; from business-planner)
- [stacks/python-fastapi-vue.md] — конвенции backend/frontend: структура app/, pydantic-settings, auth-зависимости, SQLAlchemy 2.0, Celery, Vue 3, порты по сотне на проект (python fastapi + vue; from ai-video-production через business-planner)
- [stacks/kie-ai.md] — интеграция kie.ai: Bearer, createTask/recordInfo, ловушка «HTTP 200 с ошибкой в теле» (code != 200), вебхук/поллинг, билдеры пер-модель, приоритетные фото-модели (любой проект с kie.ai; from ai-video-production через business-planner)
- [lessons/mvp-discipline.md] — MVP-дисциплина прототипа: ядро прежде обвязки, жёсткие этапы, лёгкая инфраструктура на ноль пользователей, критерий «автор сам пользуется» (любой продуктовый прототип; from jym-bro-2)
