#!/usr/bin/env bash
set -e

# Configuration with defaults
MODEL="${MLX_MODEL:-mlx-community/Qwen3.8-27B-4bit}"
HOST="${MLX_HOST:-0.0.0.0}"
PORT="${MLX_PORT:-8080}"
MAX_TOKENS="${MLX_MAX_TOKENS:-2048}"
TEMP="${MLX_TEMP:-0.2}"
TOP_P="${MLX_TOP_P:-0.85}"
KV_BITS="${MLX_KV_BITS:-4}"

echo "=========================================================="
echo "🚀 Запуск MLX Qwen 3.8 сервера (Apple Silicon M-series)"
echo "Модель:       $MODEL"
echo "Адрес:        http://$HOST:$PORT"
echo "Ризонинг:     Low (chat-template-args)"
echo "Температура:  $TEMP"
echo "KV-кэш:       ${KV_BITS}-bit (оптимизировано под 24 GB RAM)"
echo "=========================================================="

# Поиск исполняемого файла сервера (uv tool или системный PATH)
if command -v mlx_lm.server >/dev/null 2>&1; then
    SERVER_CMD="mlx_lm.server"
elif [ -x "$HOME/.local/bin/mlx_lm.server" ]; then
    SERVER_CMD="$HOME/.local/bin/mlx_lm.server"
elif [ -x "$HOME/.local/share/uv/tools/mlx-lm/bin/mlx_lm.server" ]; then
    SERVER_CMD="$HOME/.local/share/uv/tools/mlx-lm/bin/mlx_lm.server"
elif command -v uvx >/dev/null 2>&1; then
    SERVER_CMD="uvx --from mlx-lm mlx_lm.server"
else
    echo "❌ Ошибка: mlx_lm.server не найден ни в PATH, ни в ~/.local/bin/."
    echo "Установите через: uv tool install mlx-lm"
    exit 1
fi

echo "Используется исполняемый файл: $SERVER_CMD"

# Запуск OpenAI-совместимого сервера
exec $SERVER_CMD \
    --model "$MODEL" \
    --host "$HOST" \
    --port "$PORT" \
    --chat-template-args '{"reasoning_effort": "low"}' \
    --temp "$TEMP" \
    --top-p "$TOP_P" \
    --max-tokens "$MAX_TOKENS" \
    --kv-bits "$KV_BITS"
