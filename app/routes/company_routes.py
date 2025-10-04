from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Invite, UserRole
from app.auth import token_required, admin_required
from datetime import datetime, timedelta
import secrets

company_bp = Blueprint('company', __name__)

@company_bp.route('/users', methods=['GET'])
@token_required
def get_company_users(current_user):
    """Get all users in the company"""
    users = User.query.filter_by(
        company_id=current_user.company_id,
        is_active=True
    ).all()
    
    return jsonify([user.to_dict() for user in users])

@company_bp.route('/invite', methods=['POST'])
@admin_required
def create_invite(current_user):
    """Create an invite for a new user"""
    data = request.get_json()
    
    if not data.get('email') or not data.get('role'):
        return jsonify({'error': 'Email and role required'}), 400
    
    # Validate role
    try:
        role = UserRole[data['role'].upper()]
    except KeyError:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'User with this email already exists'}), 400
    
    # Check if invite already exists
    existing_invite = Invite.query.filter_by(
        email=data['email'],
        company_id=current_user.company_id,
        accepted=False
    ).first()
    
    if existing_invite:
        # Update existing invite
        existing_invite.role = role
        existing_invite.expires_at = datetime.utcnow() + timedelta(days=7)
        invite = existing_invite
    else:
        # Create new invite
        invite = Invite(
            company_id=current_user.company_id,
            email=data['email'],
            role=role,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(invite)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Invite created successfully',
        'invite': invite.to_dict(),
        'invite_link': f"{request.host_url}signup?token={invite.token}"
    }), 201

@company_bp.route('/invite/<token>', methods=['GET'])
def get_invite(token):
    """Get invite details"""
    invite = Invite.query.filter_by(token=token, accepted=False).first()
    
    if not invite:
        return jsonify({'error': 'Invite not found'}), 404
    
    if invite.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invite has expired'}), 400
    
    return jsonify({
        'email': invite.email,
        'role': invite.role.value,
        'company_name': invite.company.name
    })