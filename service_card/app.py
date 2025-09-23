import os
import json
import uuid
import pika
import mysql.connector
from datetime import datetime
import time
import socket

# --- Environment Variables (hardcoded from docker-compose.yml) ---
LOCAL_RABBIT_HOST = "localhost"
LOCAL_RABBIT_PORT = 5674
REMOTE_RABBIT_HOST = "localhost"
REMOTE_RABBIT_PORT = 5673
RABBIT_USER = "guest"
RABBIT_PASS = "guest"

MYSQL_HOST = "localhost"
MYSQL_PORT = 3308
MYSQL_USER = "root"
MYSQL_PASS = "rootpass"
MYSQL_DB = "cards_db"

# --- Helpers ---
def wait_for_port(host, port, timeout=60):
    """Wait until a TCP port is open (RabbitMQ/MySQL)."""
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"[wait] {host}:{port} is up")
                return
        except Exception:
            if time.time() - start > timeout:
                raise TimeoutError(f"Timeout waiting for {host}:{port}")
            print(f"[wait] Waiting for {host}:{port} ...")
            time.sleep(2)

# --- Database ---
def get_db():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS, database=MYSQL_DB
    )

# --- RabbitMQ ---
def rabbit_connection(host, port):
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    return pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port, credentials=credentials))

# --- Publish card back ---
def publish_card(card):
    conn = rabbit_connection(LOCAL_RABBIT_HOST, LOCAL_RABBIT_PORT)
    ch = conn.channel()
    ch.queue_declare(queue="card_queue", durable=True)
    ch.basic_publish(exchange="", routing_key="card_queue", body=json.dumps(card))
    conn.close()
    print(f"[service_card] Published card: {card['id']}")

# --- Consume users ---
def consume_users():
    while True:
        try:
            conn = rabbit_connection(REMOTE_RABBIT_HOST, REMOTE_RABBIT_PORT)
            ch = conn.channel()
            ch.queue_declare(queue="user_queue", durable=True)

            def callback(ch_, method, props, body):
                user = json.loads(body)

                # Save user
                db = get_db()
                cur = db.cursor()
                cur.execute(
                    "INSERT IGNORE INTO users (id, name, phone, entry_date, expire_date) VALUES (%s, %s, %s, %s, %s)",
                    (user["id"], user["name"], user["phone"], user["entry_date"], user["expire_date"])
                )
                db.commit()

                # Generate card
                card_id = str(uuid.uuid4())
                card = {
                    "id": card_id,
                    "user_id": user["id"],
                    "some_related_data": {"info": f"Card for {user['name']}"},
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                cur.execute(
                    "INSERT INTO cards (id, user_id, some_related_data, created_at) VALUES (%s, %s, %s, %s)",
                    (card["id"], card["user_id"], json.dumps(card["some_related_data"]), card["created_at"])
                )
                db.commit()
                cur.close()
                db.close()

                print(f"[service_card] Saved user {user['id']} and generated card {card_id}")
                publish_card(card)

            ch.basic_consume(queue="user_queue", on_message_callback=callback, auto_ack=True)
            print("[service_card] Waiting for users...")
            ch.start_consuming()
        except Exception as e:
            print(f"[service_card] User consumer error: {e}, retrying...")
            time.sleep(5)

# --- Main ---
if __name__ == "__main__":
    # Wait for dependencies
    wait_for_port(LOCAL_RABBIT_HOST, LOCAL_RABBIT_PORT)
    wait_for_port(REMOTE_RABBIT_HOST, REMOTE_RABBIT_PORT)
    wait_for_port(MYSQL_HOST, MYSQL_PORT)

    consume_users()
