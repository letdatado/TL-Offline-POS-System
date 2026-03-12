FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv==0.4.20

COPY pyproject.toml /app/pyproject.toml
COPY apps/edge/app /app/app

RUN uv pip install --system -r /app/pyproject.toml

EXPOSE 8000

CMD ["python", "-m", "app.main"]
