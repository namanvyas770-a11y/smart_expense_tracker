import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import mysql.connector
from mysql.connector import Error
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-development-secret")


def get_db():
    """Open a fresh database connection for a single request."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "expense_tracker"),
    )


CATEGORIES = [
    "Food", "Transport", "Shopping", "Education", "Bills",
    "Health", "Entertainment", "Travel", "Other"
]


def money(value):
    return float(value or 0)


def query_all(sql, params=()):
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def query_one(sql, params=()):
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def execute(sql, params=()):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def selected_month():
    value = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        datetime.strptime(value, "%Y-%m")
        return value
    except ValueError:
        return date.today().strftime("%Y-%m")


@app.route("/")
def dashboard():
    month = selected_month()
    try:
        summary = query_one("""
            SELECT
              COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) AS income,
              COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expenses,
              COUNT(*) AS transaction_count
            FROM transactions
            WHERE DATE_FORMAT(transaction_date, '%Y-%m') = %s
        """, (month,)) or {}
        summary["income"] = money(summary.get("income"))
        summary["expenses"] = money(summary.get("expenses"))
        summary["balance"] = summary["income"] - summary["expenses"]

        recent = query_all("""
            SELECT id, title, amount, type, category, transaction_date, notes
            FROM transactions
            WHERE DATE_FORMAT(transaction_date, '%Y-%m') = %s
            ORDER BY transaction_date DESC, id DESC LIMIT 8
        """, (month,))

        category_rows = query_all("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE type='expense'
              AND DATE_FORMAT(transaction_date, '%Y-%m') = %s
            GROUP BY category ORDER BY total DESC
        """, (month,))

        daily_rows = query_all("""
            SELECT DAY(transaction_date) AS day, SUM(amount) AS total
            FROM transactions
            WHERE type='expense'
              AND DATE_FORMAT(transaction_date, '%Y-%m') = %s
            GROUP BY DAY(transaction_date) ORDER BY DAY(transaction_date)
        """, (month,))

        budget_rows = query_all("""
            SELECT b.category, b.monthly_limit,
              COALESCE(SUM(t.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN transactions t
              ON t.category=b.category AND t.type='expense'
              AND DATE_FORMAT(t.transaction_date, '%Y-%m')=b.budget_month
            WHERE b.budget_month=%s
            GROUP BY b.id, b.category, b.monthly_limit
            ORDER BY b.category
        """, (month,))
        for item in budget_rows:
            item["monthly_limit"] = money(item["monthly_limit"])
            item["spent"] = money(item["spent"])
            item["percent"] = min(100, round(item["spent"] / item["monthly_limit"] * 100)) if item["monthly_limit"] else 0

        return render_template(
            "dashboard.html", month=month, summary=summary, recent=recent,
            categories=category_rows, daily=daily_rows, budgets=budget_rows
        )
    except Error as exc:
        app.logger.exception("Database error on dashboard")
        return render_template("setup_error.html", error=str(exc)), 500


@app.route("/transactions")
def transactions():
    month = selected_month()
    search = request.args.get("q", "").strip()
    kind = request.args.get("type", "").strip()
    sql = """
        SELECT id, title, amount, type, category, transaction_date, notes
        FROM transactions
        WHERE DATE_FORMAT(transaction_date, '%Y-%m') = %s
    """
    params = [month]
    if search:
        sql += " AND (title LIKE %s OR category LIKE %s OR notes LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if kind in ("income", "expense"):
        sql += " AND type=%s"
        params.append(kind)
    sql += " ORDER BY transaction_date DESC, id DESC"
    rows = query_all(sql, tuple(params))
    return render_template("transactions.html", rows=rows, month=month, q=search, kind=kind)


@app.route("/transactions/new", methods=["GET", "POST"])
def add_transaction():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        kind = request.form.get("type", "expense")
        category = request.form.get("category", "Other")
        tx_date = request.form.get("transaction_date", "")
        amount_text = request.form.get("amount", "")
        notes = request.form.get("notes", "").strip()

        try:
            amount = Decimal(amount_text)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
            if not title:
                raise ValueError("Please enter a title.")
            if kind not in ("income", "expense"):
                raise ValueError("Choose income or expense.")
            if category not in CATEGORIES:
                raise ValueError("Choose a valid category.")
            datetime.strptime(tx_date, "%Y-%m-%d")
            execute("""
                INSERT INTO transactions (title, amount, type, category, transaction_date, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (title, amount, kind, category, tx_date, notes or None))
            flash("Transaction added successfully.", "success")
            return redirect(url_for("transactions", month=tx_date[:7]))
        except (InvalidOperation, ValueError) as exc:
            flash(str(exc) or "Enter a valid amount.", "danger")
        except Error:
            app.logger.exception("Could not add transaction")
            flash("Could not save the transaction. Check your database setup.", "danger")

    return render_template("transaction_form.html", item=None, categories=CATEGORIES,
                           today=date.today().isoformat(), heading="Add transaction")


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    item = query_one("SELECT * FROM transactions WHERE id=%s", (transaction_id,))
    if not item:
        flash("Transaction not found.", "danger")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        kind = request.form.get("type", "expense")
        category = request.form.get("category", "Other")
        tx_date = request.form.get("transaction_date", "")
        amount_text = request.form.get("amount", "")
        notes = request.form.get("notes", "").strip()
        try:
            amount = Decimal(amount_text)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
            if not title:
                raise ValueError("Please enter a title.")
            if kind not in ("income", "expense") or category not in CATEGORIES:
                raise ValueError("Choose a valid type and category.")
            datetime.strptime(tx_date, "%Y-%m-%d")
            execute("""
                UPDATE transactions
                SET title=%s, amount=%s, type=%s, category=%s,
                    transaction_date=%s, notes=%s
                WHERE id=%s
            """, (title, amount, kind, category, tx_date, notes or None, transaction_id))
            flash("Transaction updated.", "success")
            return redirect(url_for("transactions", month=tx_date[:7]))
        except (InvalidOperation, ValueError) as exc:
            flash(str(exc) or "Enter a valid amount.", "danger")
        except Error:
            app.logger.exception("Could not update transaction")
            flash("Could not update the transaction. Check your database setup.", "danger")

    item["transaction_date"] = item["transaction_date"].isoformat()
    return render_template("transaction_form.html", item=item, categories=CATEGORIES,
                           today=date.today().isoformat(), heading="Edit transaction")


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
def delete_transaction(transaction_id):
    try:
        execute("DELETE FROM transactions WHERE id=%s", (transaction_id,))
        flash("Transaction deleted.", "success")
    except Error:
        app.logger.exception("Could not delete transaction")
        flash("Could not delete the transaction.", "danger")
    return redirect(request.referrer or url_for("transactions"))


@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        month = date.today().strftime("%Y-%m")

    if request.method == "POST":
        month = request.form.get("budget_month", date.today().strftime("%Y-%m"))
        category = request.form.get("category", "")
        try:
            datetime.strptime(month, "%Y-%m")
            limit = Decimal(request.form.get("monthly_limit", "0"))
            if category not in CATEGORIES:
                raise ValueError("Choose a valid category.")
            if limit <= 0:
                raise ValueError("Budget must be greater than zero.")
            execute("""
                INSERT INTO budgets (category, budget_month, monthly_limit)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE monthly_limit=VALUES(monthly_limit)
            """, (category, month, limit))
            flash("Budget saved.", "success")
            return redirect(url_for("budgets", month=month))
        except (InvalidOperation, ValueError) as exc:
            flash(str(exc) or "Enter a valid budget.", "danger")
        except Error:
            app.logger.exception("Could not save budget")
            flash("Could not save the budget. Check your database setup.", "danger")

    rows = query_all("""
        SELECT b.id, b.category, b.budget_month, b.monthly_limit,
          COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b
        LEFT JOIN transactions t
          ON t.category=b.category AND t.type='expense'
          AND DATE_FORMAT(t.transaction_date, '%Y-%m')=b.budget_month
        WHERE b.budget_month=%s
        GROUP BY b.id, b.category, b.budget_month, b.monthly_limit
        ORDER BY b.category
    """, (month,))
    for row in rows:
        row["monthly_limit"] = money(row["monthly_limit"])
        row["spent"] = money(row["spent"])
        row["percent"] = min(100, round(row["spent"] / row["monthly_limit"] * 100)) if row["monthly_limit"] else 0
    return render_template("budgets.html", rows=rows, month=month, categories=CATEGORIES)


@app.route("/budgets/<int:budget_id>/delete", methods=["POST"])
def delete_budget(budget_id):
    try:
        execute("DELETE FROM budgets WHERE id=%s", (budget_id,))
        flash("Budget deleted.", "success")
    except Error:
        app.logger.exception("Could not delete budget")
        flash("Could not delete the budget.", "danger")
    return redirect(request.referrer or url_for("budgets"))


@app.route("/health")
def health():
    try:
        row = query_one("SELECT 1 AS ok")
        return {"status": "ok", "database": bool(row and row["ok"] == 1)}
    except Error as exc:
        return {"status": "error", "database": False, "message": str(exc)}, 500


if __name__ == "__main__":
    # Debug is convenient locally. Do not enable debug mode on a public deployment.
    app.run(host="127.0.0.1", port=5000, debug=True)
