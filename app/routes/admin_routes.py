from flask import Blueprint, request, jsonify
from app import db
from app.models import (
    User, ApproverAssignment, ApprovalRule, UserRole, RuleType, Notification
)
from app.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/approver-assignments', methods=['POST'])
@admin_required
def create_approver_assignment(current_user):
    """Create or update approver assignments"""
    data = request.get_json()
    
    if not isinstance(data, list):
        return jsonify({'error': 'Expected array of assignments'}), 400
    
    # Delete existing assignments
    ApproverAssignment.query.filter_by(
        company_id=current_user.company_id
    ).delete()
    
    # Create new assignments
    for item in data:
        assignment = ApproverAssignment(
            company_id=current_user.company_id,
            sequence=item['sequence'],
            is_manager=item.get('is_manager', False)
        )
        
        if 'user_id' in item:
            assignment.user_id = item['user_id']
        elif 'role' in item:
            try:
                assignment.role = UserRole[item['role'].upper()]
            except KeyError:
                return jsonify({'error': f"Invalid role: {item['role']}"}), 400
        else:
            return jsonify({'error': 'Either user_id or role required'}), 400
        
        db.session.add(assignment)
    
    db.session.commit()
    
    return jsonify({'message': 'Approver assignments updated successfully'}), 201

@admin_bp.route('/approver-assignments', methods=['GET'])
@admin_required
def get_approver_assignments(current_user):
    """Get approver assignments for company"""
    assignments = ApproverAssignment.query.filter_by(
        company_id=current_user.company_id
    ).order_by(ApproverAssignment.sequence).all()
    
    return jsonify([a.to_dict() for a in assignments])

@admin_bp.route('/approval-rules', methods=['POST'])
@admin_required
def create_approval_rule(current_user):
    """Create conditional approval rule"""
    data = request.get_json()
    
    if not data.get('rule_type'):
        return jsonify({'error': 'rule_type required'}), 400
    
    try:
        rule_type = RuleType[data['rule_type'].upper()]
    except KeyError:
        return jsonify({'error': 'Invalid rule_type'}), 400
    
    rule = ApprovalRule(
        company_id=current_user.company_id,
        rule_type=rule_type,
        enabled=data.get('enabled', True)
    )
    
    if rule_type in [RuleType.PERCENTAGE, RuleType.HYBRID]:
        if 'percentage_threshold' not in data:
            return jsonify({'error': 'percentage_threshold required for this rule type'}), 400
        rule.percentage_threshold = data['percentage_threshold']
    
    if rule_type in [RuleType.SPECIFIC, RuleType.HYBRID]:
        if 'specific_approver_user_id' in data:
            rule.specific_approver_user_id = data['specific_approver_user_id']
        elif 'specific_approver_role' in data:
            try:
                rule.specific_approver_role = UserRole[data['specific_approver_role'].upper()]
            except KeyError:
                return jsonify({'error': 'Invalid specific_approver_role'}), 400
        else:
            return jsonify({'error': 'specific_approver_user_id or specific_approver_role required'}), 400
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify(rule.to_dict()), 201

@admin_bp.route('/approval-rules', methods=['GET'])
@admin_required
def get_approval_rules(current_user):
    """Get approval rules for company"""
    rules = ApprovalRule.query.filter_by(
        company_id=current_user.company_id
    ).all()
    
    return jsonify([r.to_dict() for r in rules])

@admin_bp.route('/approval-rules/<rule_id>', methods=['PUT'])
@admin_required
def update_approval_rule(current_user, rule_id):
    """Update approval rule"""
    rule = ApprovalRule.query.get(rule_id)
    
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    if rule.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    if 'enabled' in data:
        rule.enabled = data['enabled']
    if 'percentage_threshold' in data:
        rule.percentage_threshold = data['percentage_threshold']
    if 'specific_approver_user_id' in data:
        rule.specific_approver_user_id = data['specific_approver_user_id']
    if 'specific_approver_role' in data:
        try:
            rule.specific_approver_role = UserRole[data['specific_approver_role'].upper()]
        except KeyError:
            return jsonify({'error': 'Invalid specific_approver_role'}), 400
    
    db.session.commit()
    
    return jsonify(rule.to_dict())

@admin_bp.route('/approval-rules/<rule_id>', methods=['DELETE'])
@admin_required
def delete_approval_rule(current_user, rule_id):
    """Delete approval rule"""
    rule = ApprovalRule.query.get(rule_id)
    
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    if rule.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({'message': 'Rule deleted successfully'})

@admin_bp.route('/users/<user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(current_user, user_id):
    """Update user role"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    if 'role' in data:
        try:
            user.role = UserRole[data['role'].upper()]
        except KeyError:
            return jsonify({'error': 'Invalid role'}), 400
    
    if 'is_manager_approver' in data:
        user.is_manager_approver = data['is_manager_approver']
    
    if 'manager_id' in data:
        user.manager_id = data['manager_id']
    
    db.session.commit()
    
    return jsonify(user.to_dict())

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def deactivate_user(current_user, user_id):
    """Deactivate user"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400
    
    user.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'User deactivated successfully'})

@admin_bp.route('/users/<user_id>/activate', methods=['POST'])
@admin_required
def activate_user(current_user, user_id):
    """Activate user"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    user.is_active = True
    db.session.commit()
    
    return jsonify({'message': 'User activated successfully'})

@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user(current_user):
    """Create a new user for the company"""
    data = request.get_json()
    
    required_fields = ['email', 'password', 'full_name', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'User with this email already exists'}), 400
    
    try:
        from app.auth import hash_password
        
        role = UserRole[data['role'].upper()]
        
        user = User(
            email=data['email'],
            password_hash=hash_password(data['password']),
            full_name=data['full_name'],
            role=role,
            company_id=current_user.company_id,
            manager_id=data.get('manager_id'),
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Send notification to new user
        from app.models import Notification
        notification = Notification(
            user_id=user.id,
            title='Welcome to LedgerFlow',
            message=f'Your account has been created for {current_user.company.name}. You can now log in.',
            link='/login'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify(user.to_dict()), 201
        
    except KeyError:
        return jsonify({'error': 'Invalid role'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/add', methods=['POST'])
@admin_required
def add_existing_user(current_user):
    """Add an existing user to the company"""
    data = request.get_json()
    
    if not data.get('user_id') or not data.get('role'):
        return jsonify({'error': 'User ID and role are required'}), 400
    
    try:
        user = User.query.get(data['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.company_id == current_user.company_id:
            return jsonify({'error': 'User is already in this company'}), 400
        
        role = UserRole[data['role'].upper()]
        
        # Update user's company and role
        user.company_id = current_user.company_id
        user.role = role
        user.manager_id = data.get('manager_id')
        
        db.session.commit()
        
        # Send notification
        from app.models import Notification
        notification = Notification(
            user_id=user.id,
            title='Added to Company',
            message=f'You have been added to {current_user.company.name} as {role.value}',
            link='/dashboard'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except KeyError:
        return jsonify({'error': 'Invalid role'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
