from flask import Blueprint, request, jsonify
from app import db
from app.models import Approval, ApprovalDecision, Expense, UserRole
from app.auth import token_required
from app.approval_engine import ApprovalEngine

approval_bp = Blueprint('approval', __name__)

@approval_bp.route('/pending', methods=['GET'])
@token_required
def get_pending_approvals(current_user):
    """Get pending approvals for current user (paginated if requested). Managers see display amount in company's default currency."""
    q = Approval.query.filter_by(
        approver_id=current_user.id,
        decision=ApprovalDecision.PENDING
    ).join(Expense).filter(
        Expense.company_id == current_user.company_id
    ).order_by(Approval.created_at.desc())

    # Pagination (optional)
    try:
        page = int(request.args.get('page')) if request.args.get('page') else None
        page_size = int(request.args.get('page_size', 10)) if page else None
    except Exception:
        page, page_size = None, None

    total = q.count() if page else None
    records = q.offset((page-1)*page_size).limit(page_size).all() if page else q.all()

    # Optional conversion toggle for managers
    convert = (request.args.get('convert', 'false').lower() == 'true')

    items = []
    company_ccy = current_user.company.default_currency if current_user.company else 'INR'
    for a in records:
        item = a.to_dict(include_expense=True)
        # Only convert when explicitly requested by manager
        try:
            if current_user.role.value == 'Manager' and convert:
                from app.services.currency_service import CurrencyService
                exp = a.expense
                if str(exp.currency).upper() != company_ccy:
                    converted = CurrencyService.convert(exp.amount, str(exp.currency), company_ccy)
                    if converted is not None:
                        item['expense']['amount_display'] = float(converted)
                        item['expense']['display_currency'] = company_ccy
                else:
                    item['expense']['amount_display'] = float(exp.amount)
                    item['expense']['display_currency'] = company_ccy
        except Exception:
            pass
        items.append(item)

    if page:
        return jsonify({
            'items': items,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size if total is not None else 1
        })

    return jsonify(items)

@approval_bp.route('/<approval_id>/decision', methods=['POST'])
@token_required
def make_decision(current_user, approval_id):
    """Approve or reject an expense"""
    approval = Approval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval not found'}), 404
    
    if approval.approver_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if approval.decision != ApprovalDecision.PENDING:
        return jsonify({'error': 'Approval already processed'}), 400
    
    data = request.get_json()
    decision_str = data.get('decision', '').upper()
    
    if decision_str not in ['APPROVED', 'REJECTED']:
        return jsonify({'error': 'Invalid decision'}), 400
    
    decision = ApprovalDecision[decision_str]
    comments = data.get('comments')
    
    # Process the decision
    ApprovalEngine.process_approval_decision(approval, decision, comments)
    
    return jsonify({
        'message': f'Expense {decision.value.lower()} successfully',
        'approval': approval.to_dict(include_expense=True)
    })

@approval_bp.route('/expenses/<expense_id>', methods=['GET'])
@token_required
def get_expense_approvals(current_user, expense_id):
    """Get approval history for an expense"""
    expense = Expense.query.get(expense_id)
    
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    approvals = Approval.query.filter_by(
        expense_id=expense_id
    ).order_by(Approval.step).all()
    
    return jsonify([approval.to_dict(include_approver=True) for approval in approvals])