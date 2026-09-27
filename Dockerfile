FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["ins-ei", "--site", "/app/config/site.example.yaml", "--host", "0.0.0.0", "--port", "8080"]
