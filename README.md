# PennyPal — Personal Expense Tracker

A beginner-friendly BCA mini-project built with Python, Flask, HTML, CSS, JavaScript, and SQLite.

## Features
- User registration and login
- Password hashing
- Personal dashboard showing monthly income, expenses, and balance
- Add, edit, delete, search, and filter transactions
- Expense categories and progress bars
- Monthly reports
- Responsive layout with pastel gradients and CSS-made graphics
- SQLite database is created automatically when the app starts

## Requirements
- Windows 10/11
- Python 3.10 or newer
- VS Code (recommended)

## Run on Windows

1. Extract the ZIP file.
2. Open the `Personal_Expense_Tracker` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run the app with the virtual environment's Python directly instead (see step 7).

6. Install Flask:

   ```powershell
   python -m pip install -r requirements.txt
   ```

7. Start the app:

   ```powershell
   python app.py
   ```

   If activation did not work, use:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

8. Open this address in your browser:

   `http://127.0.0.1:5000`

9. Register an account, log in, and add your first transaction.

## Database
The `expense_tracker.db` SQLite file is generated automatically in this folder when the app starts. Keep this file to retain your data. Do not share it publicly because it contains account and transaction information.

## Important notes
- This is an educational/local project. Before deploying publicly, set a strong `SECRET_KEY`, disable debug mode, use HTTPS, and review production security.
- The demo landing page shows sample numbers as decorative graphics; your real dashboard uses the transactions you enter.
- Currency is displayed in Indian rupees (₹).

## Folder structure

```text
Personal_Expense_Tracker/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_transaction.html
│   ├── edit_transaction.html
│   ├── transactions.html
│   └── reports.html
└── static/
    ├── style.css
    └── app.js
```
