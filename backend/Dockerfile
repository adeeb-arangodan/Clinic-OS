# Python 3.12 per docs/00 §6 (locked stack)
FROM python:3.12-slim AS dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY . .

EXPOSE 8000

# Dev default; compose overrides for the celery worker service.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
