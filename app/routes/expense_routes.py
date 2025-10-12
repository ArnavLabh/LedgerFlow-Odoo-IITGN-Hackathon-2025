from flask import Blueprint, request, jsonify
from app import db
from app.models import Expense, ExpenseStatus, UserRole
from app.auth import token_required
from app.approval_engine import ApprovalEngine
from datetime import datetime

expense_bp = Blueprint('expense', __name__)

@expense_bp.route('', methods=['POST'])
@token_required
def create_expense(current_user):
    """Create a new expense"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['amount', 'category', 'description', 'date_incurred']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        expense = Expense(
            company_id=current_user.company_id,
            created_by=current_user.id,
            amount=float(data['amount']),
            currency=data.get('currency', 'INR'),
            category=data['category'],
            description=data['description'],
            date_incurred=datetime.fromisoformat(data['date_incurred']),
            status=ExpenseStatus.DRAFT
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify(expense.to_dict(include_creator=True)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@expense_bp.route('', methods=['GET'])
@token_required
def list_expenses(current_user):
    """List expenses based on user role"""
    query = Expense.query.filter_by(company_id=current_user.company_id)
    
    # Filter based on role
    if current_user.role == UserRole.EMPLOYEE:
        # Employees see only their own expenses
        query = query.filter_by(created_by=current_user.id)
    elif current_user.role == UserRole.MANAGER:
        # Managers see their team's expenses + their own
        subordinate_ids = [sub.id for sub in current_user.subordinates]
        subordinate_ids.append(current_user.id)
        query = query.filter(Expense.created_by.in_(subordinate_ids))
    # Admin sees all company expenses
    
    # Filter by status
    status = request.args.get('status')
    if status:
        try:
            status_enum = ExpenseStatus[status.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            return jsonify({'error': 'Invalid status'}), 400
    
    expenses = query.order_by(Expense.created_at.desc()).all()
    return jsonify([expense.to_dict(include_creator=True) for expense in expenses])

@expense_bp.route('/<expense_id>', methods=['GET'])
@token_required
def get_expense(current_user, expense_id):
    """Get expense details with approval history"""
    expense = Expense.query.get(expense_id)
    
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Check if user can view this expense
    if current_user.role == UserRole.EMPLOYEE and expense.created_by != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(expense.to_dict(include_approvals=True, include_creator=True))

@expense_bp.route('/<expense_id>', methods=['PUT'])
@token_required
def update_expense(current_user, expense_id):
    """Update an expense (only in DRAFT status)"""
    expense = Expense.query.get(expense_id)
    
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.created_by != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if expense.status != ExpenseStatus.DRAFT:
        return jsonify({'error': 'Can only edit draft expenses'}), 400
    
    data = request.get_json()
    
    # Update allowed fields
    if 'amount' in data:
        expense.amount = float(data['amount'])
    if 'currency' in data:
        expense.currency = data['currency']
    if 'category' in data:
        expense.category = data['category']
    if 'description' in data:
        expense.description = data['description']
    if 'date_incurred' in data:
        expense.date_incurred = datetime.fromisoformat(data['date_incurred'])
    
    expense.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(expense.to_dict())

@expense_bp.route('/<expense_id>', methods=['DELETE'])
@token_required
def delete_expense(current_user, expense_id):
    """Delete an expense (only in DRAFT status)"""
    expense = Expense.query.get(expense_id)
    
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.created_by != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if expense.status != ExpenseStatus.DRAFT:
        return jsonify({'error': 'Can only delete draft expenses'}), 400
    
    db.session.delete(expense)
    db.session.commit()
    
    return jsonify({'message': 'Expense deleted successfully'})

@expense_bp.route('/<expense_id>/submit', methods=['POST'])
@token_required
def submit_expense(current_user, expense_id):
    """Submit expense for approval"""
    try:
        expense = Expense.query.get(expense_id)
        
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        if expense.created_by != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        if expense.status != ExpenseStatus.DRAFT:
            return jsonify({'error': 'Expense already submitted'}), 400
        
        # Create approval chain
        ApprovalEngine.create_approval_chain(expense)
        
        # Refresh the expense object to get updated status
        db.session.refresh(expense)
        
        return jsonify(expense.to_dict(include_approvals=True))
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to submit expense: {str(e)}'}), 500
