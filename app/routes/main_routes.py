from flask import Blueprint, render_template, redirect, url_for, request
from app.auth import get_current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page - redirect to dashboard or login"""
    user = get_current_user()
    if user:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

@main_bp.route('/signup')
def signup():
    """Signup page"""
    token = request.args.get('token')
    return render_template('auth/signup.html', invite_token=token)

@main_bp.route('/login')
def login():
    """Login page"""
    return render_template('auth/login.html')

@main_bp.route('/dashboard')
def dashboard():
    """Dashboard - role-based view"""
    user = get_current_user()
    if not user:
        return redirect(url_for('main.login'))
    
    if user.role.value == 'Admin':
        return render_template('dashboard/admin.html', user=user)
    elif user.role.value in ['Manager', 'Finance', 'Director', 'CFO']:
        return render_template('dashboard/manager.html', user=user)
    else:
        return render_template('dashboard/employee.html', user=user)

@main_bp.route('/expenses')
def expenses():
    """Expense list page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('main.login'))
    return render_template('expenses/list.html', user=user)

@main_bp.route('/expenses/new')
def new_expense():
    """Create new expense page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('main.login'))
    return render_template('expenses/submit.html', user=user)

@main_bp.route('/expenses/<expense_id>')
def expense_detail(expense_id):
    """Expense detail page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('main.login'))
    return render_template('expenses/detail.html', user=user, expense_id=expense_id)

@main_bp.route('/approvals')
def approvals():
    """Approvals page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('main.login'))
    return render_template('dashboard/approvals.html', user=user)

@main_bp.route('/admin/config')
def admin_config():
    """Admin configuration page"""
    user = get_current_user()
    if not user or user.role.value != 'Admin':
        return redirect(url_for('main.dashboard'))
    return render_template('admin/config.html', user=user)

@main_bp.route('/notifications')
def notifications():
    """Notifications page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('main.login'))
    return render_template('notifications/list.html', user=user)