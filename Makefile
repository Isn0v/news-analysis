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

## eval-run: запустить демон оценки рыночного влияния через uv
eval-run:
	cd market-evaluator && uv run python main.py

## eval-batch: пакетная оценка всех новостей через uv
eval-batch:
	cd market-evaluator && uv run python main.py --batch --limit 100

## eval-stats: показать статистику точности прогнозов модели
eval-stats:
	cd market-evaluator && uv run python main.py --stats
