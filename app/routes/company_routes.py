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

@company_bp.route('/invites', methods=['GET'])
@admin_required
def get_pending_invites(current_user):
    """Get all pending invites for the company"""
    invites = Invite.query.filter_by(
        company_id=current_user.company_id,
        accepted=False
    ).filter(Invite.expires_at > datetime.utcnow()).all()
    
    return jsonify([invite.to_dict() for invite in invites])

@company_bp.route('/invites/<invite_id>', methods=['DELETE'])
@admin_required
def cancel_invite(current_user, invite_id):
    """Cancel an invitation"""
    invite = Invite.query.filter_by(
        id=invite_id,
        company_id=current_user.company_id
    ).first()
    
    if not invite:
        return jsonify({'error': 'Invite not found'}), 404
    
    db.session.delete(invite)
    db.session.commit()
    
    return jsonify({'message': 'Invite cancelled successfully'})

@company_bp.route('/check-admin', methods=['POST'])
def check_company_admin():
    """Check if a company already has an admin"""
    data = request.get_json()
    company_name = data.get('company_name')
    
    if not company_name:
        return jsonify({'error': 'Company name required'}), 400
    
    # Find company and check if it has an admin
    from app.models import Company
    company = Company.query.filter_by(name=company_name).first()
    
    if not company:
        return jsonify({'has_admin': False})
    
    admin_exists = User.query.filter_by(
        company_id=company.id,
        role=UserRole.ADMIN,
        is_active=True
    ).first() is not None
    
    return jsonify({'has_admin': admin_exists})
