from functools import wraps
from flask import jsonify
from app.auth import get_current_user
from app.models import UserRole

def admin_required(f):
    """Decorator to require Admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        if user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        return f(user, *args, **kwargs)
    return decorated

def manager_or_admin_required(f):
    """Decorator to require Manager-level or Admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCE, UserRole.DIRECTOR, UserRole.CFO]:
            return jsonify({'error': 'Manager access required'}), 403
        return f(user, *args, **kwargs)
    return decorated

def can_approve_expenses(f):
    """Decorator for users who can approve expenses"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_active:
            return jsonify({'error': 'Account inactive'}), 403
        if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCE, UserRole.DIRECTOR, UserRole.CFO]:
            return jsonify({'error': 'Approval permission required'}), 403
        return f(user, *args, **kwargs)
    return decorated

def can_view_all_expenses(user):
    """Check if user can view all company expenses"""
    return user.role == UserRole.ADMIN

def can_view_team_expenses(user):
    """Check if user can view team expenses"""
    return user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCE, UserRole.DIRECTOR, UserRole.CFO]

def can_manage_users(user):
    """Check if user can manage other users"""
    return user.role == UserRole.ADMIN

def can_configure_approvals(user):
    """Check if user can configure approval rules"""
    return user.role == UserRole.ADMIN

def can_override_approvals(user):
    """Check if user can override approvals"""
    return user.role == UserRole.ADMIN

def get_expense_visibility_filter(user):
    """Get SQL filter for expense visibility based on user role"""
    if can_view_all_expenses(user):
        # Admin can see all expenses in company
        return {'company_id': user.company_id}
    elif can_view_team_expenses(user):
        # Managers can see their team's expenses + their own
        from app.models import User
        team_user_ids = [u.id for u in User.query.filter_by(
            company_id=user.company_id,
            manager_id=user.id,
            is_active=True
        ).all()]
        team_user_ids.append(user.id)  # Include own expenses
        return {'created_by': team_user_ids, 'company_id': user.company_id}
    else:
        # Employees can only see their own expenses
        return {'created_by': user.id, 'company_id': user.company_id}