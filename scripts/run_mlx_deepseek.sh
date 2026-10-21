#!/usr/bin/env bash
set -e

# Configuration for DeepSeek-R1 14B on Apple Silicon
MODEL="${MLX_MODEL:-mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit}"
HOST="${MLX_HOST:-0.0.0.0}"
PORT="${MLX_PORT:-8080}"
MAX_TOKENS="${MLX_MAX_TOKENS:-3500}"
TEMP="${MLX_TEMP:-0.6}"
TOP_P="${MLX_TOP_P:-0.95}"
KV_BITS="${MLX_KV_BITS:-4}"
QUANTIZED_KV_START="${MLX_QUANTIZED_KV_START:-0}"
PREFILL_STEP_SIZE="${MLX_PREFILL_STEP_SIZE:-1024}"
PROMPT_CACHE_SIZE="${MLX_PROMPT_CACHE_SIZE:-1}"

echo "=========================================================="
echo "🚀 Запуск MLX DeepSeek-R1 14B сервера (Apple Silicon)"
echo "Модель:       $MODEL"
echo "Адрес:        http://$HOST:$PORT"
echo "Температура:  $TEMP (рекомендовано DeepSeek для R1)"
echo "Top-P:        $TOP_P"
echo "Max tokens:   $MAX_TOKENS"
echo "KV-кэш:       ${KV_BITS}-bit (старт с $QUANTIZED_KV_START)"
echo "Prefill step: $PREFILL_STEP_SIZE токенов"
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
    echo "❌ Ошибка: mlx_lm.server не найден."
    echo "Установите через: uv tool install mlx-lm"
    exit 1
fi

echo "Используется исполняемый файл: $SERVER_CMD"

# Запуск OpenAI-совместимого сервера
exec $SERVER_CMD \
    --model "$MODEL" \
    --host "$HOST" \
    --port "$PORT" \
    --temp "$TEMP" \
    --top-p "$TOP_P" \
    --max-tokens "$MAX_TOKENS" \
    --kv-bits "$KV_BITS" \
    --quantized-kv-start "$QUANTIZED_KV_START" \
    --prefill-step-size "$PREFILL_STEP_SIZE" \
    --prompt-cache-size "$PROMPT_CACHE_SIZE"
