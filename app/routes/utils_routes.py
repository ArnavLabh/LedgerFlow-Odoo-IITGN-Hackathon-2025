from flask import Blueprint, jsonify
from app.auth import token_required
from app.services.currency_service import CurrencyService

utils_bp = Blueprint('utils', __name__)

@utils_bp.route('/currencies', methods=['GET'])
@token_required
def list_currencies(current_user):
    """Return list of supported currencies code -> {name, symbol}"""
    try:
        currencies = CurrencyService.get_supported_currencies()
        # Return as array to preserve order in UI easily
        items = [{ 'code': code, **meta } for code, meta in currencies.items()]
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch currencies: {str(e)}'}), 500
