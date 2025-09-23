import pika
import json
from datetime import datetime
import uuid


def send_message(name, message):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        # Declare the queue. It's safe to run this multiple times.
        channel.queue_declare(queue='my_queue', durable=True)

        # Build JSON message with UUID as id and name field
        payload = {
            "id": str(uuid.uuid4()),  
            "name": name,              # Include user-provided name
            "message": message,        # Message body
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        channel.basic_publish(
            exchange='',
            routing_key='my_queue',
            body=json.dumps(payload).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )
        print(f" [x] Sent {payload}")
        connection.close()

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!] Failed to connect to RabbitMQ: {e}")
        print(" [!] Make sure the Docker container is running and accessible.")

if __name__ == '__main__':
    print(" [*] Producer is ready. Type your messages below.")
    print(" [*] Type 'exit' to quit.")
    
    while True:
        name_input = input("Enter your name: ")
        if name_input.lower() == 'exit':
            break

        user_input = input("Enter message: ")
        if user_input.lower() == 'exit':
            break

        if name_input and user_input:
            send_message(name_input, user_input)
