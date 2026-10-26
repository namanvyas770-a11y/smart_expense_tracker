# Smart Expense Tracker

A beginner-friendly portfolio project built with Python, Flask, and MySQL.

## Features
- Add, edit, delete, search, and filter income/expense transactions
- Monthly dashboard with income, expenses, net balance, and recent activity
- Category spending chart and daily expense chart
- Monthly budgets by category with progress indicators
- Server-side input validation and parameterized SQL queries
- Health endpoint at `/health`

## Requirements
- Python 3.10+
- MySQL Server
- MySQL Workbench (optional, useful for running the schema)

## Setup

1. Create and activate a virtual environment:

   Windows:
   ```powershell
   py -m venv .venv
   .venv\\Scripts\\activate
   ```

   macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. In MySQL Workbench, open `schema.sql` and execute it.

4. Set database environment variables before running the app.

   Windows PowerShell:
   ```powershell
   $env:DB_HOST="localhost"
   $env:DB_USER="root"
   $env:DB_PASSWORD="your_actual_mysql_password"
   $env:DB_NAME="expense_tracker"
   ```

   macOS/Linux:
   ```bash
   export DB_HOST="localhost"
   export DB_USER="root"
   export DB_PASSWORD="your_actual_mysql_password"
   export DB_NAME="expense_tracker"
   ```

5. Start the app:
   ```bash
   python app.py
   ```

6. Open `http://127.0.0.1:5000` in your browser.

## Notes
- The app uses the local MySQL account you configure. Do not put real credentials in `app.py` or upload them to GitHub.
- Debug mode is for local development only. Turn it off before deploying publicly.
- This is a learning project, not a financial service. Do not store bank login credentials or sensitive account data.
