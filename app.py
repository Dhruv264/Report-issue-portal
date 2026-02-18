from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import re

from config import Config
from db import get_db_connection
from routes.worker_routes import worker_bp   # ✅ IMPORT ONCE ONLY


app = Flask(__name__)
app.config.from_object(Config)

# REQUIRED for session + flash
app.secret_key = app.config.get("SECRET_KEY", "dev_secret_key")


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------
def init_db():
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # USERS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS userf (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ISSUES
        cur.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES userf(id) ON DELETE CASCADE,
                title VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                area VARCHAR(100),
                pincode VARCHAR(10),
                status VARCHAR(20) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # WORKERS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("DB init error:", e)


# --------------------------------------------------
# EMAIL VALIDATION
# --------------------------------------------------
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)


# --------------------------------------------------
# ROUTES (USER)
# --------------------------------------------------
@app.route('/')
def home():
    return render_template('Home.html')


@app.route('/auth')
def auth():
    return render_template('index.html')


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not email or not password:
        return jsonify(success=False, message="Please fill all fields"), 400

    if not is_valid_email(email):
        return jsonify(success=False, message="Invalid email"), 400

    if len(password) < 6:
        return jsonify(success=False, message="Password too short"), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM userf WHERE username=%s", (username,))
    if cur.fetchone():
        return jsonify(success=False, message="Username exists"), 400

    cur.execute("SELECT id FROM userf WHERE email=%s", (email,))
    if cur.fetchone():
        return jsonify(success=False, message="Email exists"), 400

    cur.execute("""
        INSERT INTO userf (username, email, password_hash)
        VALUES (%s, %s, %s)
    """, (username, email, generate_password_hash(password)))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify(success=True, redirect=url_for('auth'))


# ---------------- LOGIN ----------------
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM userf WHERE username=%s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify(success=False, message="Invalid credentials"), 401

    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify(success=True, redirect=url_for('dashboard'))


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT title, category, status, created_at
        FROM issues
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, (session['user_id'],))
    issues = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM issues
        WHERE user_id = %s
    """, (session['user_id'],))
    total_reports = cur.fetchone()['total']

    # ✅ FIXED LINE (ONLY CHANGE)
    cur.execute("""
        SELECT status, COUNT(*) AS count
        FROM issues
        WHERE user_id = %s
        GROUP BY status
    """, (session['user_id'],))

    status_rows = cur.fetchall()
    resolved = in_progress = pending = 0

    for row in status_rows:
        if row['status'] == 'Resolved':
            resolved = row['count']
        elif row['status'] == 'In Progress':
            in_progress = row['count']
        elif row['status'] == 'Pending':
            pending = row['count']

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        name=session['username'],
        issues=issues,
        total_reports=total_reports,
        resolved=resolved,
        in_progress=in_progress,
        pending=pending
    )


# ---------------- REPORT ISSUE ----------------
@app.route('/report-issue', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO issues (user_id, title, category, description, area, pincode)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            session['user_id'],
            request.form.get('title'),
            request.form.get('category'),
            request.form.get('description'),
            request.form.get('area'),
            request.form.get('pincode')
        ))

        conn.commit()
        cur.close()
        conn.close()
        flash("✅ Issue reported successfully")

        return redirect(url_for('dashboard'))

    return render_template('report_issue.html', name=session['username'])


# ---------------- MY ISSUES ----------------
@app.route('/my-issues')
def my_issues():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT title, category, status, created_at
        FROM issues
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session['user_id'],))

    issues = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('my_issues.html', issues=issues, name=session['username'])


# ---------------- DELETE ISSUES ----------------
@app.route('/delete-issues', methods=['GET', 'POST'])
def delete_issues():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        issue_ids = [int(i) for i in request.form.getlist('issue_ids')]

        if issue_ids:
            cur.execute("""
                DELETE FROM issues
                WHERE id = ANY(%s::int[]) AND user_id = %s
            """, (issue_ids, session['user_id']))
            conn.commit()

        cur.close()
        conn.close()
        return redirect(url_for('delete_issues'))

    cur.execute("""
        SELECT id, title, category, status, created_at
        FROM issues
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session['user_id'],))

    issues = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('delete_issues.html', issues=issues)


# ---------------- LOGOUT ----------------
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


# --------------------------------------------------
# REGISTER WORKER BLUEPRINT (ONCE)
# --------------------------------------------------
app.register_blueprint(worker_bp)


# --------------------------------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
