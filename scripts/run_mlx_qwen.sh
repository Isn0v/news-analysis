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

# Проверяем наличие модуля mlx_lm
if ! python3 -c "import mlx_lm" >/dev/null 2>&1; then
    echo "⚠️ Пакет mlx_lm не найден. Устанавливаем через uv/pip..."
    if command -v uv >/dev/null 2>&1; then
        uv pip install --system mlx-lm || uv pip install mlx-lm
    else
        pip install mlx-lm
    fi
fi

# Запуск OpenAI-совместимого сервера
exec python3 -m mlx_lm.server \
    --model "$MODEL" \
    --host "$HOST" \
    --port "$PORT" \
    --chat-template-args '{"reasoning_effort": "low"}' \
    --temp "$TEMP" \
    --top-p "$TOP_P" \
    --max-tokens "$MAX_TOKENS" \
    --kv-bits "$KV_BITS"
