# Message Durability and Reliability Improvements

This document explains the changes made to ensure no data is lost and messages are properly handled.

## Key Improvements

### 1. Message Persistence
- **Queue Durability**: Both `user_queue` and `card_queue` are declared as `durable=True`
- **Message Persistence**: All published messages use `delivery_mode=2` to persist to disk
- **Benefit**: Messages survive RabbitMQ server restarts

### 2. Manual Acknowledgments
- **Changed from**: `auto_ack=True` 
- **Changed to**: `auto_ack=False` with manual `basic_ack()` and `basic_nack()`
- **Benefit**: Messages are only removed from queue after successful processing

### 3. Quality of Service (QoS)
- **Setting**: `basic_qos(prefetch_count=1)`
- **Benefit**: Each consumer processes only one message at a time, preventing message loss during crashes

### 4. Error Handling and Requeuing

#### User Service (Card Consumer)
```python
try:
    # Process card and save to database
    card = json.loads(body)
    # ... database operations ...
    
    # Only acknowledge after successful database save
    ch_.basic_ack(delivery_tag=method.delivery_tag)
    
except Exception as e:
    # Reject message and requeue it for retry
    ch_.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

#### Card Service (User Consumer)
```python
try:
    # Save user and create card
    # ... database operations ...
    # ... publish card ...
    
    # Only acknowledge after everything is successful
    ch_.basic_ack(delivery_tag=method.delivery_tag)
    
except Exception as e:
    # Rollback database and requeue message
    if db:
        db.rollback()
    ch_.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

### 5. Transaction Safety

#### Database Operations
- **User Creation**: Database save happens first, then queue publication
- **Card Processing**: All operations (save user, create card, publish card) must succeed before ack
- **Rollback**: Database rollback on errors

#### Processing Flow
1. **Receive Message**: Message stays in queue (not acknowledged)
2. **Process Data**: Save to database, perform operations
3. **Publish Response**: Send any required response messages
4. **Acknowledge**: Only after all operations succeed
5. **On Error**: Rollback database, reject message with requeue=True

## Failure Scenarios Handled

### Scenario 1: Database Connection Fails
- **Before**: Message lost, no retry
- **After**: Message requeued, will retry when service recovers

### Scenario 2: Card Service Receives User but Fails to Create Card
- **Before**: User message acknowledged, card never created
- **After**: User message requeued, will retry until card is successfully created

### Scenario 3: Card Service Creates Card but Fails to Publish
- **Before**: Card created but user service never receives it
- **After**: Database rollback, user message requeued, entire process retries

### Scenario 4: User Service Receives Card but Fails to Save
- **Before**: Card message lost
- **After**: Card message requeued, will retry until successfully saved

### Scenario 5: Container Crashes During Processing
- **Before**: All in-flight messages lost
- **After**: Unacknowledged messages return to queue, processing resumes

## Benefits

1. **Zero Data Loss**: Messages persist to disk and are requeued on failures
2. **Exactly-Once Processing**: Manual acknowledgments ensure messages are processed completely
3. **Automatic Retry**: Failed messages are automatically requeued
4. **Consistency**: Database and message queue stay in sync
5. **Fault Tolerance**: System recovers gracefully from failures

## Monitoring

The improved logging shows:
- When messages are being processed
- When messages are successfully acknowledged
- When messages are requeued due to errors
- Database transaction status

Example logs:
```
[service_card] Processing user: abc123
[service_card] Successfully processed user abc123, created card def456, and acked message

[service_user] Processing card: def456 for user abc123
[service_user] Successfully saved and acked card: def456 for user abc123
```

## Testing Failure Scenarios

You can test the durability by:

1. **Kill containers during processing**: Messages will requeue
2. **Temporarily break database connections**: Messages will requeue and retry
3. **Restart RabbitMQ**: Persistent messages will still be there
4. **Check queue lengths**: Unprocessed messages remain in queues

## Queue Management

To monitor queues:
- RabbitMQ Management UI: http://localhost:15673 (card service)
- RabbitMQ Management UI: http://localhost:15674 (user service)
- Check message counts, processing rates, and error rates