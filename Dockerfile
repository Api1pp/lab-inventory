FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY app.py .
RUN mkdir -p /var/lib/backend_data

EXPOSE 5000
CMD ["python", "app.py"]