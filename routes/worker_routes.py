from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
from db import get_db_connection

worker_bp = Blueprint('worker', __name__)

# ---------------- WORKER AUTH PAGE ----------------
@worker_bp.route('/worker_auth')
@worker_bp.route('/worker')
def worker_auth():
    return render_template('worker_auth.html')


# ---------------- WORKER REGISTER ----------------
@worker_bp.route('/worker/register', methods=['POST'])
def worker_register():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        category = request.form.get('category')

        if not all([name, email, password, category]):
            return jsonify({'success': False, 'message': 'All fields required'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM workers WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Worker already exists'}), 400

        password_hash = generate_password_hash(password)

        cur.execute("""
            INSERT INTO workers (name, email, password_hash, category, status)
            VALUES (%s, %s, %s, %s, 'available')
            RETURNING id
        """, (name, email, password_hash, category))

        worker_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        session['worker_id'] = worker_id
        session['worker_name'] = name

        return jsonify({'success': True, 'redirect': url_for('worker.worker_dashboard')})

    except Exception as e:
        print("WORKER REGISTER ERROR:", e)
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ---------------- WORKER LOGIN ----------------
@worker_bp.route('/worker/login', methods=['POST'])
def worker_login():
    try:
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM workers WHERE email=%s", (email,))
        worker = cur.fetchone()

        cur.close()
        conn.close()

        if worker and check_password_hash(worker['password_hash'], password):
            session['worker_id'] = worker['id']
            session['worker_name'] = worker['name']

            return jsonify({'success': True, 'redirect': url_for('worker.worker_dashboard')})

        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print("WORKER LOGIN ERROR:", e)
        return jsonify({'success': False, 'message': 'Server error'}), 500


# ---------------- WORKER DASHBOARD ----------------
@worker_bp.route('/worker/dashboard')
def worker_dashboard():
    if 'worker_id' not in session:
        return redirect(url_for('worker.worker_auth'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # get worker status
    cur.execute("SELECT status FROM workers WHERE id=%s", (session['worker_id'],))
    worker = cur.fetchone()

    # get assigned issues
    cur.execute("""
        SELECT id, title, category, description, area, status, created_at
        FROM issues
        WHERE worker_id = %s
        ORDER BY created_at DESC
    """, (session['worker_id'],))

    issues = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'WorkerDashboard.html',
        issues=issues,
        worker_name=session.get('worker_name'),
        worker_status=worker['status']
    )


# ---------------- TOGGLE WORKER STATUS (NEW) ----------------
@worker_bp.route('/worker/toggle-status', methods=['POST'])
def toggle_worker_status():
    if 'worker_id' not in session:
        return jsonify({'success': False}), 401

    new_status = request.form.get('status')
    if new_status not in ['available', 'unavailable']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE workers
        SET status=%s
        WHERE id=%s
    """, (new_status, session['worker_id']))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'success': True})


# ---------------- UPDATE ISSUE STATUS ----------------
@worker_bp.route('/worker/update-status', methods=['POST'])
def update_issue_status():
    if 'worker_id' not in session:
        return jsonify({'success': False}), 401

    issue_id = request.form.get('issue_id')
    status = request.form.get('status')

    if status not in ['Pending', 'In Progress', 'Resolved']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE issues
        SET status=%s
        WHERE id=%s AND worker_id=%s
    """, (status, issue_id, session['worker_id']))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'success': True})


# ---------------- WORKER LOGOUT ----------------
@worker_bp.route('/worker/logout')
def worker_logout():
    session.clear()
    return redirect('/')
