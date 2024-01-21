FROM python:3.8-slim

WORKDIR /app
COPY script.py .

ENTRYPOINT ["python", "/app/script.py"]
