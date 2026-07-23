FROM python:3.11-slim

WORKDIR /app

# OS deps for cryptography wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 PORT=8000
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
