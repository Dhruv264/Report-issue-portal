from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import re
from routes.worker_routes import worker_bp
from routes.admin_routes import admin_bp
from config import Config
from db import get_db_connection
from werkzeug.utils import secure_filename
import os
import uuid

# =========================
# FLASK APP (FIXED)
# =========================
app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static'
)

app.config.from_object(Config)
app.secret_key = app.config.get("SECRET_KEY", "dev_secret_key")

# =========================
# UPLOAD CONFIG (FIXED)
# =========================
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --------------------------------------------------
# HOME / AUTH
# --------------------------------------------------
@app.route('/')
def home():
    logged_in = 'user_id' in session
    
    # Fetch statistics from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Total issues (exclude rejected)
    cur.execute("SELECT COUNT(*) FROM issues WHERE status != 'Rejected'")
    total_issues = cur.fetchone()[0] or 0
    
    # Resolved issues
    cur.execute("SELECT COUNT(*) FROM issues WHERE status = 'Resolved'")
    resolved_issues = cur.fetchone()[0] or 0
    
    # Active issues (Pending + In Progress + Accepted)
    cur.execute("SELECT COUNT(*) FROM issues WHERE status IN ('Pending', 'In Progress', 'Accepted')")
    active_issues = cur.fetchone()[0] or 0
    
    cur.close()
    conn.close()
    
    return render_template('Home.html', logged_in=logged_in, 
                         total_issues=total_issues, 
                         resolved_issues=resolved_issues, 
                         active_issues=active_issues)

@app.route('/auth')
def auth():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/user-home')
def user_home():
    if 'user_id' not in session:
        return redirect(url_for('auth'))
    
    # Fetch statistics from database
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Total issues (exclude rejected)
    cur.execute("SELECT COUNT(*) FROM issues WHERE status != 'Rejected'")
    total_issues = cur.fetchone()[0] or 0
    
    # Resolved issues
    cur.execute("SELECT COUNT(*) FROM issues WHERE status = 'Resolved'")
    resolved_issues = cur.fetchone()[0] or 0
    
    # Active issues (Pending + In Progress + Accepted)
    cur.execute("SELECT COUNT(*) FROM issues WHERE status IN ('Pending', 'In Progress', 'Accepted')")
    active_issues = cur.fetchone()[0] or 0
    
    cur.close()
    conn.close()
    
    return render_template('user.html', 
                         total_issues=total_issues, 
                         resolved_issues=resolved_issues, 
                         active_issues=active_issues)


# --------------------------------------------------
# SIGNUP
# --------------------------------------------------
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not email or not password:
        return jsonify(success=False, message="Please fill all fields"), 400

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return jsonify(success=False, message="Invalid email"), 400

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


# --------------------------------------------------
# LOGIN
# --------------------------------------------------
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


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT title, category, status, created_at, rejection_reason
        FROM issues
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, (session['user_id'],))
    issues = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('dashboard.html', name=session['username'], issues=issues)


# --------------------------------------------------
# REPORT ISSUE (PHOTO FIXED)
# --------------------------------------------------
@app.route('/report-issue', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    if request.method == 'POST':
        photo_filename = None

        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{uuid.uuid4()}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO issues (
                user_id, title, category, description, area, pincode, photo_filename
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session['user_id'],
            request.form.get('title'),
            request.form.get('category'),
            request.form.get('description'),
            request.form.get('area'),
            request.form.get('pincode'),
            photo_filename
        ))

        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Issue reported successfully")
        return redirect(url_for('dashboard'))

    return render_template('report_issue.html')


# --------------------------------------------------
# MY ISSUES (🔥 MAIN FIX HERE)
# --------------------------------------------------
@app.route('/my-issues')
def my_issues():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            title,
            category,
            status,
            created_at,
            photo_filename,
            rejection_reason
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
        issue_ids = request.form.getlist('issue_ids')

        if issue_ids:
            cur.execute("""
                DELETE FROM issues
                WHERE id = ANY(%s::int[])
                AND user_id = %s
            """, (issue_ids, session['user_id']))
            conn.commit()

        cur.close()
        conn.close()
        flash("🗑️ Selected issues deleted successfully")
        return redirect(url_for('delete_issues'))

    cur.execute("""
        SELECT id, title, category, status, created_at, photo_filename, rejection_reason
        FROM issues
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session['user_id'],))

    issues = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('delete_issues.html', issues=issues)

# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


# --------------------------------------------------
# BLUEPRINTS
# --------------------------------------------------
app.register_blueprint(worker_bp)
app.register_blueprint(admin_bp)


# --------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
