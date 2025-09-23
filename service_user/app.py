import os
import json
import uuid
import pika
import mysql.connector
from datetime import datetime, timedelta
import threading
import time
import socket

# --- Environment Variables (hardcoded from docker-compose.yml) ---
LOCAL_RABBIT_HOST = "localhost"
LOCAL_RABBIT_PORT = 5673
REMOTE_RABBIT_HOST = "localhost"
REMOTE_RABBIT_PORT = 5674
RABBIT_USER = "guest"
RABBIT_PASS = "guest"

MYSQL_HOST = "localhost"
MYSQL_PORT = 3307
MYSQL_USER = "root"
MYSQL_PASS = "rootpass"
MYSQL_DB = "users_db"

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

# --- Publish user ---
def publish_user(user_data):
    conn = rabbit_connection(LOCAL_RABBIT_HOST, LOCAL_RABBIT_PORT)
    ch = conn.channel()
    ch.queue_declare(queue="user_queue", durable=True)
    ch.basic_publish(exchange="", routing_key="user_queue", body=json.dumps(user_data))
    conn.close()
    print(f"[service_user] Published user: {user_data['id']}")

# --- Consume cards ---
def consume_cards():
    while True:
        try:
            conn = rabbit_connection(REMOTE_RABBIT_HOST, REMOTE_RABBIT_PORT)
            ch = conn.channel()
            ch.queue_declare(queue="card_queue", durable=True)

            def callback(ch_, method, props, body):
                card = json.loads(body)
                db = get_db()
                cur = db.cursor()
                cur.execute(
                    "INSERT INTO user_cards (id, user_id, card_data) VALUES (%s, %s, %s)",
                    (card["id"], card["user_id"], json.dumps(card))
                )
                db.commit()
                cur.close()
                db.close()
                print(f"[service_user] Saved card: {card['id']} for user {card['user_id']}")

            ch.basic_consume(queue="card_queue", on_message_callback=callback, auto_ack=True)
            print("[service_user] Waiting for cards...")
            ch.start_consuming()
        except Exception as e:
            print(f"[service_user] Card consumer error: {e}, retrying...")
            time.sleep(5)

# --- Generate user ---
def generate_user():
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "name": "User_" + user_id[:8],
        "phone": "1234567890",
        "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expire_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"),
    }

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO users (id, name, phone, entry_date, expire_date) VALUES (%s, %s, %s, %s, %s)",
        (user["id"], user["name"], user["phone"], user["entry_date"], user["expire_date"])
    )
    db.commit()
    cur.close()
    db.close()

    publish_user(user)

# --- Main ---
if __name__ == "__main__":
    # Wait for dependencies
    wait_for_port(LOCAL_RABBIT_HOST, LOCAL_RABBIT_PORT)
    wait_for_port(REMOTE_RABBIT_HOST, REMOTE_RABBIT_PORT)
    wait_for_port(MYSQL_HOST, MYSQL_PORT)

    threading.Thread(target=consume_cards, daemon=True).start()

    print("Press Enter to generate a new user... (Ctrl+C to quit)")
    while True:
        input()
        generate_user()
