from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "expense_tracker.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-local-development")


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('income', 'expense')),
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                transaction_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


@app.template_filter("money")
def money(value):
    try:
        return "₹{:,.2f}".format(float(value or 0))
    except (ValueError, TypeError):
        return "₹0.00"


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
        elif len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                        (name, email, generate_password_hash(password))
                    )
                flash("Account created successfully. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("An account with that email already exists.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Welcome back, {}!".format(user["name"]), "success")
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    selected_month = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        datetime.strptime(selected_month, "%Y-%m")
    except ValueError:
        selected_month = date.today().strftime("%Y-%m")

    with get_db() as db:
        totals = db.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN kind='income' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN kind='expense' THEN amount ELSE 0 END), 0) AS expenses
            FROM transactions
            WHERE user_id = ? AND substr(transaction_date, 1, 7) = ?
        """, (user_id, selected_month)).fetchone()

        recent = db.execute("""
            SELECT * FROM transactions
            WHERE user_id = ? AND substr(transaction_date, 1, 7) = ?
            ORDER BY transaction_date DESC, id DESC LIMIT 8
        """, (user_id, selected_month)).fetchall()

        categories = db.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id = ? AND kind='expense' AND substr(transaction_date, 1, 7) = ?
            GROUP BY category ORDER BY total DESC
        """, (user_id, selected_month)).fetchall()

        all_count = db.execute(
            "SELECT COUNT(*) AS count FROM transactions WHERE user_id = ? AND substr(transaction_date, 1, 7) = ?",
            (user_id, selected_month)
        ).fetchone()["count"]

    income = float(totals["income"])
    expenses = float(totals["expenses"])
    category_total = sum(float(item["total"]) for item in categories)
    chart_categories = [
        {"name": item["category"], "total": float(item["total"]),
         "percent": round((float(item["total"]) / category_total * 100), 1) if category_total else 0}
        for item in categories
    ]

    return render_template(
        "dashboard.html",
        income=income,
        expenses=expenses,
        balance=income-expenses,
        recent=recent,
        categories=chart_categories,
        selected_month=selected_month,
        transaction_count=all_count
    )


@app.route("/transactions")
@login_required
def transactions():
    kind = request.args.get("kind", "all")
    search = request.args.get("search", "").strip()
    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [session["user_id"]]

    if kind in ("income", "expense"):
        query += " AND kind = ?"
        params.append(kind)
    if search:
        query += " AND (category LIKE ? OR description LIKE ?)"
        params.extend(["%" + search + "%", "%" + search + "%"])

    query += " ORDER BY transaction_date DESC, id DESC"
    with get_db() as db:
        rows = db.execute(query, params).fetchall()

    return render_template("transactions.html", transactions=rows, kind=kind, search=search)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        kind = request.form.get("kind", "")
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        amount_text = request.form.get("amount", "").strip()
        transaction_date = request.form.get("transaction_date", "")

        try:
            amount = float(amount_text)
        except ValueError:
            amount = 0

        try:
            datetime.strptime(transaction_date, "%Y-%m-%d")
            valid_date = True
        except ValueError:
            valid_date = False

        if kind not in ("income", "expense"):
            flash("Choose income or expense.", "error")
        elif amount <= 0:
            flash("Enter an amount greater than zero.", "error")
        elif not category:
            flash("Please choose a category.", "error")
        elif not valid_date:
            flash("Choose a valid date.", "error")
        else:
            with get_db() as db:
                db.execute("""
                    INSERT INTO transactions (user_id, kind, amount, category, description, transaction_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session["user_id"], kind, amount, category, description, transaction_date))
            flash("Transaction added successfully.", "success")
            return redirect(url_for("dashboard"))

    return render_template("add_transaction.html", today=date.today().isoformat())


@app.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    user_id = session["user_id"]
    with get_db() as db:
        transaction = db.execute(
            "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
            (transaction_id, user_id)
        ).fetchone()

        if transaction is None:
            flash("Transaction not found.", "error")
            return redirect(url_for("transactions"))

        if request.method == "POST":
            kind = request.form.get("kind", "")
            category = request.form.get("category", "").strip()
            description = request.form.get("description", "").strip()
            transaction_date = request.form.get("transaction_date", "")
            try:
                amount = float(request.form.get("amount", "0"))
            except ValueError:
                amount = 0

            try:
                datetime.strptime(transaction_date, "%Y-%m-%d")
                valid_date = True
            except ValueError:
                valid_date = False

            if kind not in ("income", "expense") or amount <= 0 or not category or not valid_date:
                flash("Please enter valid transaction details.", "error")
            else:
                db.execute("""
                    UPDATE transactions
                    SET kind=?, amount=?, category=?, description=?, transaction_date=?
                    WHERE id=? AND user_id=?
                """, (kind, amount, category, description, transaction_date, transaction_id, user_id))
                flash("Transaction updated.", "success")
                return redirect(url_for("transactions"))

    return render_template("edit_transaction.html", transaction=transaction)


@app.route("/delete/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    with get_db() as db:
        db.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (transaction_id, session["user_id"])
        )
    flash("Transaction deleted.", "success")
    return redirect(url_for("transactions"))


@app.route("/reports")
@login_required
def reports():
    user_id = session["user_id"]
    with get_db() as db:
        monthly = db.execute("""
            SELECT substr(transaction_date, 1, 7) AS month,
                SUM(CASE WHEN kind='income' THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN kind='expense' THEN amount ELSE 0 END) AS expenses
            FROM transactions WHERE user_id = ?
            GROUP BY substr(transaction_date, 1, 7)
            ORDER BY month DESC LIMIT 6
        """, (user_id,)).fetchall()
        category_rows = db.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id = ? AND kind='expense'
            GROUP BY category ORDER BY total DESC LIMIT 8
        """, (user_id,)).fetchall()

    months = list(reversed(monthly))
    max_value = max([max(float(r["income"] or 0), float(r["expenses"] or 0)) for r in months] or [1])
    monthly_data = [{
        "month": row["month"],
        "income": float(row["income"] or 0),
        "expenses": float(row["expenses"] or 0),
        "income_pct": round(float(row["income"] or 0) / max_value * 100, 1),
        "expenses_pct": round(float(row["expenses"] or 0) / max_value * 100, 1)
    } for row in months]
    return render_template("reports.html", monthly=monthly_data, categories=category_rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)


# Initialize the database when the application starts
init_db()

if __name__ == "__main__":
    app.run(debug=True)
