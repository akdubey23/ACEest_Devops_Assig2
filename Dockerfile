# ACEest Fitness API — production-style image for coursework / CI
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Leverage Docker layer cache: deps change less often than app code
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

# app.py binds to 0.0.0.0:5000
CMD ["python", "app.py"]
