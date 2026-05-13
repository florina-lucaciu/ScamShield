FROM mcr.microsoft.com/playwright/python:v1.59.0-jammy
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 10000
CMD ["gunicorn", "--workers", "1", "--threads", "1", "--timeout", "120", "-b", "0.0.0.0:10000", "app:app"]