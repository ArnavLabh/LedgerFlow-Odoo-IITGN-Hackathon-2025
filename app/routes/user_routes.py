from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Expense, Approval
from app.auth import token_required, hash_password, verify_password
from sqlalchemy import func

user_bp = Blueprint('user', __name__)

@user_bp.route('/me', methods=['GET'])
@token_required
def get_current_user_profile(current_user):
    """Get current user profile"""
    return jsonify(current_user.to_dict(include_company=True))

@user_bp.route('/all', methods=['GET'])
@token_required
def get_all_users(current_user):
    """Get all users across all companies (for admin invite purposes)"""
    # Only allow admins to see all users
    if current_user.role.value != 'Admin':
        return jsonify({'error': 'Access denied'}), 403
    
    users = User.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role.value,
        'company_name': user.company.name if user.company else None
    } for user in users])

@user_bp.route('/stats', methods=['GET'])
@token_required
def get_user_stats(current_user):
    """Get user statistics for profile page"""
    # Get expense count
    expense_count = Expense.query.filter_by(created_by=current_user.id).count()
    
    # Get approval count (if user can approve)
    approval_count = 0
    if current_user.role.value in ['Manager', 'Finance', 'Director', 'CFO', 'Admin']:
        approval_count = Approval.query.filter_by(approver_id=current_user.id).count()
    
    return jsonify({
        'expense_count': expense_count,
        'approval_count': approval_count
    })

@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update user profile"""
    data = request.get_json()
    
    # Update allowed fields
    if 'full_name' in data and data['full_name'].strip():
        current_user.full_name = data['full_name'].strip()
    
    # Handle password change
    if data.get('current_password') and data.get('new_password'):
        if not current_user.password_hash:
            return jsonify({'error': 'Cannot change password for OAuth-only accounts'}), 400
        
        if not verify_password(data['current_password'], current_user.password_hash):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        if len(data['new_password']) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400
        
        current_user.password_hash = hash_password(data['new_password'])
    
    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500
