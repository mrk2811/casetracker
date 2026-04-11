FROM python:3.12-slim

# Install Chromium, ChromeDriver, and required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    # libs needed by Chromium / Selenium
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# Tell Selenium where to find the browser / driver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

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
