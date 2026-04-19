FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV EVOLVER_PORT=16888
ENV EVOLVER_HTTP_HOST=0.0.0.0

EXPOSE 16888

CMD ["python", "-m", "evolver.server"]