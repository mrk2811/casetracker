FROM python:3.12-slim

WORKDIR /app

# Install Poetry (no virtualenv needed inside Docker)
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

# Copy dependency manifests first for layer caching
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --only main

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
