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
