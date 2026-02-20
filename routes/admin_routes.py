from flask import Blueprint, render_template, request, session, redirect, url_for
from psycopg2.extras import RealDictCursor
from db import get_db_connection

admin_bp = Blueprint('admin', __name__)

# ---------------- ADMIN LOGIN PAGE ----------------
@admin_bp.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')


# ---------------- ADMIN LOGIN LOGIC ----------------
@admin_bp.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == 'admin' and password == 'ADMIN123@123':
        session['admin_logged_in'] = True
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin_login.html', error="Invalid admin credentials")


# ---------------- ADMIN DASHBOARD ----------------
@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 🔹 TOTAL REPORTS (exclude rejected issues)
    cur.execute("SELECT COUNT(*) AS total FROM issues WHERE status != 'Rejected'")
    total_reports = cur.fetchone()['total']

    # 🔹 PENDING REPORTS
    cur.execute("SELECT COUNT(*) AS pending FROM issues WHERE status = 'Pending'")
    pending_reports = cur.fetchone()['pending']

    # 🔹 ASSIGNED WORKS
    cur.execute("SELECT COUNT(*) AS assigned FROM issues WHERE status = 'In Progress'")
    assigned_works = cur.fetchone()['assigned']

    # 🔹 RECENT ISSUES (exclude rejected issues)
    cur.execute("""
        SELECT id, title, area, category, status, created_at
        FROM issues
        WHERE status != 'Rejected'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    recent_issues = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_reports=total_reports,
        pending_reports=pending_reports,
        assigned_works=assigned_works,
        recent_issues=recent_issues
    )


# ---------------- ADMIN LOGOUT ----------------
@admin_bp.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')


# ==================================================
# 🔥 NEW CODE BELOW (ASSIGN WORKER FEATURE)
# 🔥 NOTHING ABOVE WAS DELETED OR CHANGED
# ==================================================

# ---------------- ASSIGN WORKER PAGE ----------------
@admin_bp.route('/admin/assign/<int:issue_id>')
def assign_worker(issue_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get issue details
    cur.execute("""
        SELECT id, title, category
        FROM issues
        WHERE id = %s
    """, (issue_id,))
    issue = cur.fetchone()

    # Get available workers of same category
    cur.execute("""
        SELECT id, name, email
        FROM workers
        WHERE status = 'available'
        AND category = %s
    """, (issue['category'],))

    workers = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'assign_worker.html',
        issue=issue,
        workers=workers
    )


# ---------------- ASSIGN WORKER ACTION ----------------
@admin_bp.route('/admin/assign-worker', methods=['POST'])
def assign_worker_post():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    issue_id = request.form.get('issue_id')
    worker_id = request.form.get('worker_id')

    conn = get_db_connection()
    cur = conn.cursor()

    # Assign worker & update status
    cur.execute("""
        UPDATE issues
        SET worker_id = %s,
            status = 'In Progress'
        WHERE id = %s
    """, (worker_id, issue_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin.admin_dashboard'))


# ============================================================
# 🟢 ACCEPT ISSUE (Admin accepts the reported issue)
# ============================================================
@admin_bp.route('/admin/accept-issue/<int:issue_id>', methods=['POST'])
def accept_issue(issue_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # Update issue status to Accepted (or keep as Pending for assignment)
    cur.execute("""
        UPDATE issues
        SET status = 'Accepted'
        WHERE id = %s
    """, (issue_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin.admin_dashboard'))


# ============================================================
# 🔴 REJECT ISSUE (Admin rejects the reported issue)
# ============================================================
@admin_bp.route('/admin/reject-issue/<int:issue_id>', methods=['POST'])
def reject_issue(issue_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    rejection_reason = request.form.get('rejection_reason', '').strip()

    conn = get_db_connection()
    cur = conn.cursor()

    # Update issue status to Rejected with reason
    cur.execute("""
        UPDATE issues
        SET status = 'Rejected', rejection_reason = %s
        WHERE id = %s
    """, (rejection_reason, issue_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin.admin_dashboard'))


