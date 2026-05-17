FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
RUN playwright install-deps

EXPOSE 10000
CMD ["gunicorn", "--workers", "1", "--threads", "1", "--timeout", "120", "-b", "0.0.0.0:10000", "app:app"]