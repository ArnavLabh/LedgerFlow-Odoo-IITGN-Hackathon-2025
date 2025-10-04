from flask import Blueprint, jsonify
from app.auth import token_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Get current user information"""
    return jsonify(current_user.to_dict(include_company=True))