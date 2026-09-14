.PHONY: lint index test gc stats install
lint:      ## проверить формат единиц знания
	python3 tools/knowledge.py lint
index:     ## пересобрать knowledge/INDEX.md
	python3 tools/knowledge.py index
test:      ## офлайн-евалы: триггеры уроков срабатывают на эталонных промтах
	python3 tools/knowledge.py lint && python3 tools/knowledge.py index --check && python3 tools/evals.py
test-live: ## платные евалы через claude -p (см. evals/cases.json)
	python3 tools/evals.py --live
gc:        ## отчёт уборки базы знаний
	python3 tools/knowledge.py gc
stats:
	python3 tools/knowledge.py stats
install:   ## подключить глобальные хуки и скиллы к ~/.claude
	bash tools/install.sh
