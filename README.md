# RabbitMQ with MySQL Setup

## Prerequisites

Install the required Python package:
```bash
pip install pika
```

## Starting Services

Start MySQL and RabbitMQ using Docker Compose:
```bash
docker-compose up -d
```

## Running the Application

### Terminal 1 - Start Consumer
```bash
cd consumer
python consumer.py
```

### Terminal 2 - Start Producer
```bash
cd producer
python producer.py
```

## Service Details

- **MySQL**: Available on port 3307
  - Username: `my_user`
  - Password: `my_password`
  - Database: `messages_db`

- **RabbitMQ**: Available on port 5672
  - Management UI: http://localhost:15672
  - Username: `guest`
  - Password: `guest`

## Stopping Services

```bash
docker-compose down
```