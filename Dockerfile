FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsnap7-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["python", "main.py"]