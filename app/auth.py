import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from app.models import User, RefreshToken, UserRole
from app import db

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_access_token(user_id, company_id, role):
    """Generate JWT access token"""
    payload = {
        'user_id': user_id,
        'company_id': company_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')

def generate_refresh_token(user_id):
    """Generate and store refresh token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
    
    # Store in database
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(seconds=current_app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    )
    db.session.add(refresh_token)
    db.session.commit()
    
    return token

def verify_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def revoke_refresh_token(token):
    """Revoke a refresh token"""
    refresh_token = RefreshToken.query.filter_by(token=token).first()
    if refresh_token:
        refresh_token.revoked = True
        db.session.commit()
        return True
    return False

def get_current_user():
    """Get current user from JWT token in request headers or cookies"""
    token = None
    
    # Check Authorization header first (for API requests)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    
    # Fallback to checking cookies (for browser requests)
    if not token:
        # Try to get access token from cookies
        token = request.cookies.get('access_token')
        
        # If no access token in cookies, try to use refresh token to get user info
        if not token:
            refresh_token = request.cookies.get('refresh_token')
            if refresh_token:
                # Verify refresh token and get user
                payload = verify_token(refresh_token)
                if payload:
                    # Check if refresh token is still valid in database
                    refresh_record = RefreshToken.query.filter_by(token=refresh_token).first()
                    if refresh_record and not refresh_record.revoked:
                        user = User.query.get(payload['user_id'])
                        return user
    
    if not token:
        return None
    
    payload = verify_token(token)
    if not payload:
        return None
    
    user = User.query.get(payload['user_id'])
    return user

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_active:
            return jsonify({'error': 'User account is inactive'}), 403
        return f(user, *args, **kwargs)
    return decorated

def role_required(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            if not user.is_active:
                return jsonify({'error': 'User account is inactive'}), 403
            if user.role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(user, *args, **kwargs)
        return decorated
    return decorator

def admin_required(f):
    """Decorator to require Admin role"""
    return role_required(UserRole.ADMIN)(f)

def manager_or_admin_required(f):
    """Decorator to require Manager or Admin role"""
    return role_required(UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCE, UserRole.DIRECTOR, UserRole.CFO)(f)