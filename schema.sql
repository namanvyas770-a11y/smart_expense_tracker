CREATE DATABASE IF NOT EXISTS expense_tracker
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE expense_tracker;

CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    type ENUM('income','expense') NOT NULL DEFAULT 'expense',
    category VARCHAR(40) NOT NULL DEFAULT 'Other',
    transaction_date DATE NOT NULL,
    notes VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_transactions_date (transaction_date),
    INDEX idx_transactions_type_category (type, category)
);

CREATE TABLE IF NOT EXISTS budgets (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(40) NOT NULL,
    budget_month CHAR(7) NOT NULL,
    monthly_limit DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_budget_category_month (category, budget_month)
);
