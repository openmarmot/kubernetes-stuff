FROM python:3.11-alpine

RUN apk add --no-cache iputils shadow

RUN useradd -m appuser

WORKDIR /app

COPY code/ .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "app.py"]