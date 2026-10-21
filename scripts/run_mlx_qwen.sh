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
QUANTIZED_KV_START="${MLX_QUANTIZED_KV_START:-0}"
PREFILL_STEP_SIZE="${MLX_PREFILL_STEP_SIZE:-512}"
PROMPT_CACHE_SIZE="${MLX_PROMPT_CACHE_SIZE:-1}"
ENABLE_THINKING="${MLX_ENABLE_THINKING:-true}"
REASONING_EFFORT="${MLX_REASONING_EFFORT:-low}"

# Настройка ризонинга: по умолчанию low, но можно отключить через MLX_ENABLE_THINKING=false
if [ "$ENABLE_THINKING" = "false" ] || [ "$ENABLE_THINKING" = "0" ]; then
    CHAT_TEMPLATE_ARGS='{"enable_thinking": false}'
    THINKING_LABEL="Отключен (быстрый прямой вывод)"
else
    CHAT_TEMPLATE_ARGS="{\"enable_thinking\": true, \"reasoning_effort\": \"$REASONING_EFFORT\"}"
    THINKING_LABEL="Включен ($REASONING_EFFORT)"
fi

echo "=========================================================="
echo "🚀 Запуск MLX Qwen 3.8 сервера (Apple Silicon M-series)"
echo "Модель:       $MODEL"
echo "Адрес:        http://$HOST:$PORT"
echo "Ризонинг:     $THINKING_LABEL"
echo "Температура:  $TEMP"
echo "KV-кэш:       ${KV_BITS}-bit (старт с токена $QUANTIZED_KV_START)"
echo "Prefill step: $PREFILL_STEP_SIZE токенов"
echo "Cache size:   $PROMPT_CACHE_SIZE сессия"
echo "Max tokens:   $MAX_TOKENS"
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

# Запуск OpenAI-совместимого сервера с оптимизацией памяти под 24 GB RAM
exec $SERVER_CMD \
    --model "$MODEL" \
    --host "$HOST" \
    --port "$PORT" \
    --chat-template-args "$CHAT_TEMPLATE_ARGS" \
    --temp "$TEMP" \
    --top-p "$TOP_P" \
    --max-tokens "$MAX_TOKENS" \
    --kv-bits "$KV_BITS" \
    --quantized-kv-start "$QUANTIZED_KV_START" \
    --prefill-step-size "$PREFILL_STEP_SIZE" \
    --prompt-cache-size "$PROMPT_CACHE_SIZE"
