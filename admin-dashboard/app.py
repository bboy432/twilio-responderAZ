import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import requests
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-this-secret-key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# Configuration
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'axiomadmin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Dannyle44!')
NOTIFICATION_PHONE = os.environ.get('NOTIFICATION_PHONE', '+18017104034')

# Branch URLs
BRANCHES = {
    'tuc': {
        'name': 'Tucson',
        'url': os.environ.get('TUC_URL', 'http://twilio-app-tuc:5000'),
        'public_url': os.environ.get('TUC_PUBLIC_URL', 'https://tuc.axiom-emergencies.com')
    },
    'poc': {
        'name': 'Pocatello',
        'url': os.environ.get('POC_URL', 'http://twilio-app-poc:5000'),
        'public_url': os.environ.get('POC_PUBLIC_URL', 'https://poc.axiom-emergencies.com')
    },
    'rex': {
        'name': 'Rexburg',
        'url': os.environ.get('REX_URL', 'http://twilio-app-rex:5000'),
        'public_url': os.environ.get('REX_PUBLIC_URL', 'https://rex.axiom-emergencies.com')
    }
}

# Twilio configuration for notifications
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/data/admin.db')


# Database functions
def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # User permissions table
    c.execute('''CREATE TABLE IF NOT EXISTS user_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        branch TEXT NOT NULL,
        can_view INTEGER DEFAULT 1,
        can_trigger INTEGER DEFAULT 0,
        can_disable INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, branch)
    )''')
    
    # Branch status table
    c.execute('''CREATE TABLE IF NOT EXISTS branch_status (
        branch TEXT PRIMARY KEY,
        is_enabled INTEGER DEFAULT 1,
        disabled_at TIMESTAMP,
        disabled_by TEXT,
        last_check TIMESTAMP
    )''')
    
    # Initialize branch statuses
    for branch in BRANCHES.keys():
        c.execute('''INSERT OR IGNORE INTO branch_status (branch, is_enabled, last_check) 
                     VALUES (?, 1, CURRENT_TIMESTAMP)''', (branch,))
    
    # Create default admin user if not exists
    admin_hash = hashlib.sha256((ADMIN_PASSWORD).encode()).hexdigest()
    c.execute('''INSERT OR IGNORE INTO users (username, password_hash, is_admin) 
                 VALUES (?, ?, 1)''', (ADMIN_USERNAME, admin_hash))
    
    conn.commit()
    conn.close()


def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    password_hash = hash_password(password)
    c.execute('SELECT id, is_admin FROM users WHERE username = ? AND password_hash = ?',
              (username, password_hash))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {'id': result[0], 'username': username, 'is_admin': bool(result[1])}
    return None


def get_user_permissions(user_id):
    """Get permissions for a user"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT branch, can_view, can_trigger, can_disable 
                 FROM user_permissions WHERE user_id = ?''', (user_id,))
    permissions = {}
    for row in c.fetchall():
        permissions[row[0]] = {
            'can_view': bool(row[1]),
            'can_trigger': bool(row[2]),
            'can_disable': bool(row[3])
        }
    
    conn.close()
    return permissions


def is_branch_enabled(branch):
    """Check if a branch is enabled"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('SELECT is_enabled FROM branch_status WHERE branch = ?', (branch,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else True


def set_branch_status(branch, enabled, username):
    """Enable or disable a branch"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    if enabled:
        c.execute('''UPDATE branch_status 
                     SET is_enabled = 1, disabled_at = NULL, disabled_by = NULL 
                     WHERE branch = ?''', (branch,))
    else:
        c.execute('''UPDATE branch_status 
                     SET is_enabled = 0, disabled_at = CURRENT_TIMESTAMP, disabled_by = ? 
                     WHERE branch = ?''', (username, branch))
    
    conn.commit()
    conn.close()


def send_sms_notification(message):
    """Send SMS notification to admin"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print(f"SMS notification not configured. Would send: {message}")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=NOTIFICATION_PHONE
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False


def get_branch_status(branch_key):
    """Get status from a branch instance"""
    try:
        url = BRANCHES[branch_key]['url']
        response = requests.get(f"{url}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'online': True,
                'status': data.get('status', 'Unknown'),
                'message': data.get('message', ''),
                'enabled': is_branch_enabled(branch_key)
            }
    except Exception as e:
        print(f"Error checking {branch_key}: {e}")
    
    return {
        'online': False,
        'status': 'Offline',
        'message': 'Cannot connect to branch instance',
        'enabled': is_branch_enabled(branch_key)
    }


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
@login_required
def dashboard():
    """Main dashboard showing all branches"""
    branch_statuses = {}
    for branch_key, branch_info in BRANCHES.items():
        branch_statuses[branch_key] = {
            **branch_info,
            **get_branch_status(branch_key)
        }
    
    user_permissions = {}
    if not session.get('is_admin'):
        user_permissions = get_user_permissions(session['user_id'])
    
    return render_template('dashboard.html',
                         branches=branch_statuses,
                         user_permissions=user_permissions,
                         is_admin=session.get('is_admin', False))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = verify_user(username, password)
        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/branch/<branch>/status')
@login_required
def branch_status_api(branch):
    """API endpoint for branch status"""
    if branch not in BRANCHES:
        return jsonify({'error': 'Invalid branch'}), 404
    
    # Check permissions
    if not session.get('is_admin'):
        perms = get_user_permissions(session['user_id'])
        if branch not in perms or not perms[branch]['can_view']:
            return jsonify({'error': 'Permission denied'}), 403
    
    status = get_branch_status(branch)
    return jsonify(status)


@app.route('/api/branch/<branch>/disable', methods=['POST'])
@login_required
def disable_branch(branch):
    """Disable a branch"""
    if branch not in BRANCHES:
        return jsonify({'error': 'Invalid branch'}), 404
    
    # Check permissions
    if not session.get('is_admin'):
        perms = get_user_permissions(session['user_id'])
        if branch not in perms or not perms[branch]['can_disable']:
            return jsonify({'error': 'Permission denied'}), 403
    
    confirm = request.json.get('confirm', False)
    if not confirm:
        return jsonify({'error': 'Confirmation required'}), 400
    
    set_branch_status(branch, False, session['username'])
    
    # Send SMS notification
    branch_name = BRANCHES[branch]['name']
    message = f"ALERT: {branch_name} branch has been DISABLED by {session['username']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_sms_notification(message)
    
    return jsonify({'success': True, 'message': f'{branch_name} branch disabled'})


@app.route('/api/branch/<branch>/enable', methods=['POST'])
@login_required
def enable_branch(branch):
    """Enable a branch"""
    if branch not in BRANCHES:
        return jsonify({'error': 'Invalid branch'}), 404
    
    # Check permissions
    if not session.get('is_admin'):
        perms = get_user_permissions(session['user_id'])
        if branch not in perms or not perms[branch]['can_disable']:
            return jsonify({'error': 'Permission denied'}), 403
    
    set_branch_status(branch, True, session['username'])
    
    # Send SMS notification
    branch_name = BRANCHES[branch]['name']
    message = f"INFO: {branch_name} branch has been ENABLED by {session['username']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_sms_notification(message)
    
    return jsonify({'success': True, 'message': f'{branch_name} branch enabled'})


@app.route('/users')
@admin_required
def users():
    """User management page"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT id, username, is_admin, created_at FROM users ORDER BY created_at DESC''')
    users_list = []
    for row in c.fetchall():
        user_perms = get_user_permissions(row[0])
        users_list.append({
            'id': row[0],
            'username': row[1],
            'is_admin': bool(row[2]),
            'created_at': row[3],
            'permissions': user_perms
        })
    
    conn.close()
    return render_template('users.html', users=users_list, branches=BRANCHES)


@app.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    """Create a new user"""
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if not username or not password:
        flash('Username and password are required', 'error')
        return redirect(url_for('users'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                 (username, password_hash, 1 if is_admin else 0))
        user_id = c.lastrowid
        
        # Set up default permissions for non-admin users
        if not is_admin:
            for branch in BRANCHES.keys():
                can_view = request.form.get(f'perm_{branch}_view') == 'on'
                can_trigger = request.form.get(f'perm_{branch}_trigger') == 'on'
                can_disable = request.form.get(f'perm_{branch}_disable') == 'on'
                
                c.execute('''INSERT INTO user_permissions 
                             (user_id, branch, can_view, can_trigger, can_disable) 
                             VALUES (?, ?, ?, ?, ?)''',
                         (user_id, branch, 1 if can_view else 0, 
                          1 if can_trigger else 0, 1 if can_disable else 0))
        
        conn.commit()
        flash(f'User {username} created successfully', 'success')
    except sqlite3.IntegrityError:
        flash(f'User {username} already exists', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    if user_id == session['user_id']:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('users'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('DELETE FROM user_permissions WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('users'))


@app.route('/branch/<branch>')
@login_required
def branch_dashboard(branch):
    """Individual branch dashboard"""
    if branch not in BRANCHES:
        flash('Invalid branch', 'error')
        return redirect(url_for('dashboard'))
    
    # Check permissions
    if not session.get('is_admin'):
        perms = get_user_permissions(session['user_id'])
        if branch not in perms or not perms[branch]['can_view']:
            flash('Permission denied', 'error')
            return redirect(url_for('dashboard'))
    
    branch_info = BRANCHES[branch]
    status = get_branch_status(branch)
    
    return render_template('branch_dashboard.html',
                         branch_key=branch,
                         branch=branch_info,
                         status=status,
                         is_admin=session.get('is_admin', False))


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    # Initialize database
    init_db()
    
    print("=" * 60)
    print("Admin Dashboard Starting")
    print(f"Database: {DATABASE_PATH}")
    print(f"Default admin: {ADMIN_USERNAME}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
