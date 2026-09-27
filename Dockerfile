FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY plugins ./plugins

RUN pip install --no-cache-dir .

RUN mkdir -p /app/data

EXPOSE 8080
CMD ["ins-ei", "--site", "/app/config/site.example.yaml", "--plugins", "/app/plugins", "--data", "/app/data", "--host", "0.0.0.0", "--port", "8080"]
