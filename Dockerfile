FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8017

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data/jobs

EXPOSE 8017

CMD ["sh", "-c", "python -m uvicorn handdraft.main:app --host 0.0.0.0 --port ${PORT}"]
