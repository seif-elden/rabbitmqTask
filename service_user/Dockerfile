FROM python:3.11-slim

WORKDIR /app

COPY app.py .

RUN pip install pika mysql-connector-python flask

EXPOSE 5000

CMD ["python", "app.py"]
