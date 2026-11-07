
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install production dependencies
RUN uv sync --frozen --no-dev

# Use the virtual environment created by uv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source code
COPY . .

# Python runtime configuration
ENV PYTHONUNBUFFERED=1

# Backend port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
