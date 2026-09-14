FROM python:3.12-slim

# Копируем бинарник uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

# Копируем файлы манифестов для кэширования слоёв сборки
COPY pyproject.toml ./

# Синхронизируем зависимости
RUN uv sync --no-install-project

# Копируем остальной код
COPY . .

# Устанавливаем сам проект
RUN uv sync

CMD ["uv", "run", "python", "main.py"]
