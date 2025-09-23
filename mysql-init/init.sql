CREATE TABLE IF NOT EXISTS messages (
    id CHAR(36) PRIMARY KEY,   -- UUID string
    name TEXT NOT NULL,        -- Sender's name
    body TEXT NOT NULL,        -- Message body
    received_time DATETIME NOT NULL
);
