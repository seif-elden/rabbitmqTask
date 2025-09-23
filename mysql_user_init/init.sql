CREATE DATABASE IF NOT EXISTS users_db;
USE users_db;

CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  phone VARCHAR(50),
  entry_date DATETIME,
  expire_date DATETIME
);

CREATE TABLE IF NOT EXISTS user_cards (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36),
  card_data JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
