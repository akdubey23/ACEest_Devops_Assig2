# ACEest Fitness API - multi-stage image for CI tests and runtime
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Leverage Docker layer cache: deps change less often than app code
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app.py .

FROM base AS test
COPY tests ./tests
COPY scripts ./scripts
RUN mkdir -p test-results allure-results \
    && python -m pytest tests/ -v --tb=short \
      --junitxml=test-results/junit.xml \
      --cov=app --cov-report=xml:test-results/coverage.xml \
      --html=test-results/pytest-report.html --self-contained-html

FROM base AS runtime

EXPOSE 5000

# app.py binds to 0.0.0.0:5000
CMD ["python", "app.py"]
