FROM python:3.12-slim

WORKDIR /app
COPY script.py .

ENTRYPOINT ["python", "/app/script.py"]
