from flask import Blueprint, request, jsonify
from app import db
from app.models import Expense, ExpenseStatus, UserRole
from app.auth import token_required
from app.approval_engine import ApprovalEngine
from datetime import datetime
import os
import re
from werkzeug.utils import secure_filename

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

expense_bp = Blueprint('expense', __name__)

@expense_bp.route('', methods=['POST'])
@token_required
def create_expense(current_user):
    """Create a new expense"""
    # Enforce: only Employees can create/submit expenses (Admin, Manager cannot)
    from app.models import UserRole
    if current_user.role != UserRole.EMPLOYEE:
        return jsonify({'error': 'Only employees can submit expenses'}), 403

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
    """List expenses based on user role. For managers, optional conversion to company currency."""
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
    
    # Optional conversion for managers
    convert = request.args.get('convert', 'false').lower() == 'true'
    company_ccy = current_user.company.default_currency if current_user.company else 'INR'

    # Pagination (optional). If page present, return a paginated object; otherwise, return list for backward-compat.
    try:
        page = int(request.args.get('page')) if request.args.get('page') else None
        page_size = int(request.args.get('page_size', 10)) if page else None
    except Exception:
        page, page_size = None, None

    q = query.order_by(Expense.created_at.desc())

    total = q.count() if page else None
    records = q.offset((page-1)*page_size).limit(page_size).all() if page else q.all()

    items = []
    for exp in records:
        data = exp.to_dict(include_creator=True)
        if current_user.role == UserRole.MANAGER and convert:
            try:
                from app.services.currency_service import CurrencyService
                if str(exp.currency).upper() != company_ccy:
                    converted = CurrencyService.convert(exp.amount, str(exp.currency), company_ccy)
                    if converted is not None:
                        data['amount_display'] = float(converted)
                        data['display_currency'] = company_ccy
                else:
                    data['amount_display'] = float(exp.amount)
                    data['display_currency'] = company_ccy
            except Exception:
                pass
        items.append(data)

    if page:
        return jsonify({
            'items': items,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size if total is not None else 1
        })

    return jsonify(items)

@expense_bp.route('/<expense_id>', methods=['GET'])
@token_required
def get_expense(current_user, expense_id):
    """Get expense details with approval history. For managers, include converted display amount."""
    expense = Expense.query.get(expense_id)
    
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404
    
    if expense.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Check if user can view this expense
    if current_user.role == UserRole.EMPLOYEE and expense.created_by != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = expense.to_dict(include_approvals=True, include_creator=True)

    # Add display conversion for managers
    try:
        if current_user.role.value == 'Manager':
            company_ccy = current_user.company.default_currency if current_user.company else 'INR'
            if str(expense.currency).upper() != company_ccy:
                from app.services.currency_service import CurrencyService
                converted = CurrencyService.convert(expense.amount, str(expense.currency), company_ccy)
                if converted is not None:
                    data['amount_display'] = float(converted)
                    data['display_currency'] = company_ccy
            else:
                data['amount_display'] = float(expense.amount)
                data['display_currency'] = company_ccy
    except Exception:
        pass

    return jsonify(data)

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

@expense_bp.route('/ocr', methods=['POST'])
@token_required
def ocr_receipt(current_user):
    """OCR endpoint to extract expense data from receipt image.
    Accepts multipart/form-data with 'receipt' file.
    """
    # Only employees can create expenses via OCR
    from app.models import UserRole
    if current_user.role != UserRole.EMPLOYEE:
        return jsonify({'error': 'Only employees can scan receipts'}), 403

    if 'receipt' not in request.files:
        return jsonify({'error': 'No receipt file provided'}), 400

    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if pytesseract is None or Image is None:
        return jsonify({'error': 'OCR not available. Please install Tesseract OCR and pillow.'}), 501

    uploads_dir = os.path.join('uploads', 'receipts')
    os.makedirs(uploads_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    path = os.path.join(uploads_dir, filename)
    file.save(path)

    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)

        # Basic parsing
        amount = None
        # Match money like 1,234.56 or 1234.56
        money_matches = re.findall(r"(?:Rs\.?\s*)?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+\.[0-9]{2})", text)
        if money_matches:
            # take the max value as amount
            try:
                amount = max(float(m.replace(',', '')) for m in money_matches)
            except Exception:
                amount = None

        # Date like 2025-10-12 or 12/10/2025
        date_str = None
        date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text)
        if date_match:
            date_str = date_match.group(1)

        # Merchant - take first non-empty line
        merchant = None
        for line in text.splitlines():
            line = line.strip()
            if len(line) > 2 and not re.search(r"\d", line):
                merchant = line
                break

        suggestion = {
            'amount': amount,
            'currency': current_user.preferred_currency or (current_user.company.default_currency if current_user.company else 'INR'),
            'date_incurred': date_str,
            'description': f"Expense at {merchant}" if merchant else '',
            'merchant': merchant,
            'raw_text': text
        }
        return jsonify({'suggestion': suggestion})
    except Exception as e:
        return jsonify({'error': f'OCR failed: {str(e)}'}), 500

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
