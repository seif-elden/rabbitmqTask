CREATE TABLE IF NOT EXISTS messages (
    id CHAR(36) PRIMARY KEY,   -- UUID string
    body TEXT NOT NULL,
    received_time DATETIME NOT NULL
);
