from flask import Blueprint, request, jsonify
from app import db
from app.models import (
    User, ApproverAssignment, ApprovalRule, UserRole, RuleType
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