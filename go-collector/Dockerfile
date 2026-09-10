FROM golang:1.27.0-alpine AS builder

WORKDIR /app

# Копируем манифесты и vendor — сеть не нужна
COPY go.mod go.sum ./
COPY vendor/ vendor/

# Копируем исходники
COPY . .

# Собираем бинарь из локального vendor (без обращения к proxy.golang.org)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -mod=vendor -o collector ./main.go

# Финальный минимальный образ
FROM alpine:latest

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/collector .

CMD ["./collector"]