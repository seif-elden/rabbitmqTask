import os
import json
import uuid
import pika
import mysql.connector
from datetime import datetime, timedelta
import threading
import time
import socket
from flask import Flask, request, jsonify

# --- Environment Variables (hardcoded from docker-compose.yml) ---
LOCAL_RABBIT_HOST = "rabbitmq_user"
LOCAL_RABBIT_PORT = 5672
REMOTE_RABBIT_HOST = "rabbitmq_card"
REMOTE_RABBIT_PORT = 5672
RABBIT_USER = "guest"
RABBIT_PASS = "guest"

MYSQL_HOST = "mysql_user"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASS = "rootpass"
MYSQL_DB = "users_db"

# --- Flask App ---
app = Flask(__name__)

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
def create_user(user_data=None):
    user_id = str(uuid.uuid4())
    
    # Use provided data or generate default data
    if user_data:
        user = {
            "id": user_id,
            "name": user_data.get("name", "User_" + user_id[:8]),
            "phone": user_data.get("phone", "1234567890"),
            "entry_date": user_data.get("entry_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "expire_date": user_data.get("expire_date", (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")),
        }
    else:
        user = {
            "id": user_id,
            "name": "User_" + user_id[:8],
            "phone": "1234567890",
            "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expire_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"),
        }

    try:
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
        return user
    except Exception as e:
        print(f"[service_user] Error creating user: {e}")
        raise e

# --- API Endpoints ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "user_service"}), 200

@app.route('/users', methods=['POST'])
def create_user_endpoint():
    try:
        user_data = request.get_json() if request.is_json else None
        user = create_user(user_data)
        return jsonify({
            "message": "User created successfully",
            "user": user
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users ORDER BY entry_date DESC")
        users = cur.fetchall()
        cur.close()
        db.close()
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if user:
            # Get user's cards too
            cur.execute("SELECT * FROM user_cards WHERE user_id = %s", (user_id,))
            cards = cur.fetchall()
            user['cards'] = cards
        
        cur.close()
        db.close()
        
        if user:
            return jsonify({"user": user}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Initialize and start services ---
def init_services():
    # Wait for dependencies
    wait_for_port(LOCAL_RABBIT_HOST, LOCAL_RABBIT_PORT)
    wait_for_port(REMOTE_RABBIT_HOST, REMOTE_RABBIT_PORT)
    wait_for_port(MYSQL_HOST, MYSQL_PORT)

    # Start card consumer in background thread
    threading.Thread(target=consume_cards, daemon=True).start()
    print("[service_user] Card consumer started")

# --- Main ---
if __name__ == "__main__":
    init_services()
    print("[service_user] Starting Flask API server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
