import pika
import mysql.connector
import time

# --- Database Connection Setup ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3307,  # Use the correct port from your docker command
            user="my_user",
            password="my_password",
            database="messages_db"
        )
        print(" [✓] Database connection established.")
        return conn
    except mysql.connector.Error as err:
        print(f" [!] Database connection failed: {err}")
        return None
    

# --- RabbitMQ and Consumer Logic  ---
def on_message_received(ch, method, properties, body):
    try:
        message_body = body.decode()
        print(f" [x] Received '{message_body}'")

        # Use the global db connection to insert the data
        cursor = db_connection.cursor()
        sql = "INSERT INTO messages (content) VALUES (%s)"
        cursor.execute(sql, (message_body,))
        db_connection.commit()
        
        print(f" [✓] Saved message to database.")

    except mysql.connector.Error as e:
        print(f" [!] Database write failed: {e}")
        db_connection.rollback()
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    global db_connection
    db_connection = get_db_connection()
    if db_connection is None:
        return

    try:
        # --- Create table logic added here ---
        cursor = db_connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                content TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_connection.commit()
        print(" [✓] 'messages' table ensured to exist.")
        cursor.close()
        
        # --- RabbitMQ Connection starts after table is ready ---
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='my_queue' , durable=True)
        channel.basic_qos(prefetch_count=1)

        print(' [*] Waiting for messages. To exit press CTRL+C')
        channel.basic_consume(queue='my_queue', on_message_callback=on_message_received, auto_ack=False)
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!] Failed to connect to RabbitMQ: {e}")
    except KeyboardInterrupt:
        print(" [*] Consumer stopped.")
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()
        if db_connection and db_connection.is_connected():
            db_connection.close()
            print(" [x] Database connection closed.")

if __name__ == '__main__':
    start_consumer()