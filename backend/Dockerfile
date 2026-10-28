FROM python:3.15.0-slim-bookworm

# Copy uv binary from official Astral image
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation and use copy link mode for cached layers
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=never

# Copy dependency definition files first for caching
COPY pyproject.toml uv.lock .python-version ./

# Install project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy application source code
COPY . /app

# Place virtual environment on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Render sets PORT dynamically (defaults to 8000 for local runs)
ENV PORT=8000
EXPOSE 8000

CMD ["python", "-m", "app.cli.start"]
