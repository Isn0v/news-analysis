.PHONY: up down stop vendor

## up: собрать образы и запустить все сервисы в фоне
up:
	docker compose up --build -d

## down: остановить и удалить контейнеры, сети и volumes
down:
	docker compose down -v

## stop: остановить контейнеры без удаления данных
stop:
	docker compose down

## vendor: обновить vendor/ для go-collector
vendor:
	cd go-collector && go mod tidy && go mod vendor

## llm-run: запустить воркер анализа сентимента через uv
llm-run:
	cd llm && uv run python main.py

## ollama-setup: настроить увеличенный контекст (16k) для локальной модели DeepSeek в Ollama
ollama-setup:
	@printf "FROM deepseek-r1:14b\nPARAMETER num_ctx 16384\n" > /tmp/Modelfile.deepseek && \
	ollama create deepseek-r1:14b -f /tmp/Modelfile.deepseek && \
	rm /tmp/Modelfile.deepseek

## qwen-ollama-setup: создать оптимизированную модель qwen-fast в Ollama (num_ctx 8192, temp 0.2, low reasoning)
qwen-ollama-setup:
	ollama create qwen-fast -f models/Modelfile.qwen

## mlx-serve: запустить высокоскоростной локальный MLX-сервер Qwen 3.8 на Apple Silicon (порт 8080)
mlx-serve:
	./scripts/run_mlx_qwen.sh

## llm-reset: сбросить статус обработки новостей и подготовить к повторному инференсу
llm-reset:
	docker compose exec -T db psql -U trader -d crypto_news -c "UPDATE raw_news SET processed = FALSE, processed_at = NULL, llm_result = NULL; TRUNCATE TABLE news_market_impact;"


## eval-run: запустить демон оценки рыночного влияния через uv
eval-run:
	cd market-evaluator && uv run python main.py

## eval-batch: пакетная оценка всех новостей через uv
eval-batch:
	cd market-evaluator && uv run python main.py --batch --limit 100

## eval-stats: показать статистику точности прогнозов модели
eval-stats:
	cd market-evaluator && uv run python main.py --stats

## db-export: экспортировать все данные из БД в CSV и JSON (./market-evaluator/exports/)
db-export:
	cd market-evaluator && uv run python export.py --output-dir ./exports

## db-export-combined: экспортировать только итоговую объединённую таблицу (статья + LLM + рынок)
db-export-combined:
	cd market-evaluator && uv run python export.py --only combined --output-dir ./exports

## test-collector: запустить тесты go-collector (с цветным выводом)
test-collector:
	@cd go-collector && if command -v gotestsum >/dev/null 2>&1; then \
		gotestsum --format testdox; \
	elif [ -x "$$HOME/go/bin/gotestsum" ]; then \
		"$$HOME/go/bin/gotestsum" --format testdox; \
	else \
		go test -v ./...; \
	fi

## test-llm: запустить тесты llm сервиса
test-llm:
	cd llm && uv run python -m pytest -v

## test-eval: запустить тесты market-evaluator
test-eval:
	cd market-evaluator && uv run python -m pytest -v

## test: запустить тесты по всем микросервисам
test: test-collector test-llm test-eval

