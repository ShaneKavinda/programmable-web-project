FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5051
ENV AUX_DB_PATH=/app/data/notifications.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 5051

CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT} app:app"]
