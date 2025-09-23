# User Service API Documentation

The User Service now runs as a REST API that can be accessed via HTTP requests.

## Base URL
```
http://localhost:5000
```

## Endpoints

### 1. Health Check
- **GET** `/health`
- **Description**: Check if the service is running
- **Response**: 
  ```json
  {
    "status": "healthy",
    "service": "user_service"
  }
  ```

### 2. Create User
- **POST** `/users`
- **Description**: Create a new user
- **Request Body** (JSON, optional):
  ```json
  {
    "name": "John Doe",
    "phone": "1234567890",
    "entry_date": "2025-09-23 10:00:00",
    "expire_date": "2025-10-23 10:00:00"
  }
  ```
- **Response**:
  ```json
  {
    "message": "User created successfully",
    "user": {
      "id": "uuid-here",
      "name": "John Doe",
      "phone": "1234567890",
      "entry_date": "2025-09-23 10:00:00",
      "expire_date": "2025-10-23 10:00:00"
    }
  }
  ```

### 3. Get All Users
- **GET** `/users`
- **Description**: Retrieve all users
- **Response**:
  ```json
  {
    "users": [
      {
        "id": "uuid-here",
        "name": "John Doe",
        "phone": "1234567890",
        "entry_date": "2025-09-23 10:00:00",
        "expire_date": "2025-10-23 10:00:00"
      }
    ]
  }
  ```

### 4. Get User by ID
- **GET** `/users/{user_id}`
- **Description**: Retrieve a specific user and their cards
- **Response**:
  ```json
  {
    "user": {
      "id": "uuid-here",
      "name": "John Doe",
      "phone": "1234567890",
      "entry_date": "2025-09-23 10:00:00",
      "expire_date": "2025-10-23 10:00:00",
      "cards": [
        {
          "id": "card-uuid",
          "user_id": "uuid-here",
          "card_data": "{...card details...}"
        }
      ]
    }
  }
  ```

## Example Usage

### Create a user with curl:
```bash
curl -X POST http://localhost:5000/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "phone": "9876543210"
  }'
```

### Create a user with default values:
```bash
curl -X POST http://localhost:5000/users
```

### Get all users:
```bash
curl http://localhost:5000/users
```

### Health check:
```bash
curl http://localhost:5000/health
```

## Running the Service

1. Start the services with docker-compose:
   ```bash
   docker-compose up --build
   ```

2. The API will be available at `http://localhost:5000`

3. The service will automatically:
   - Connect to RabbitMQ and MySQL
   - Start consuming cards from the card service
   - Publish new users to the message queue

## Notes

- All user data is automatically published to RabbitMQ for the card service to consume
- Cards created by the card service are automatically stored in the user database
- The service includes health checking and automatic retry logic for robust operation