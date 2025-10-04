from flask import Blueprint, request, jsonify, make_response, current_app
from app import db
from app.models import User, Company, UserRole, RefreshToken, Invite
from app.auth import (
    hash_password, verify_password, generate_access_token,
    generate_refresh_token, verify_token, revoke_refresh_token,
    token_required
)
import requests
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Sign up new user and create company"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'full_name']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Check for invite token
        invite_token = data.get('invite_token')
        if invite_token:
            invite = Invite.query.filter_by(token=invite_token, accepted=False).first()
            if not invite:
                return jsonify({'error': 'Invalid or expired invite'}), 400
            if invite.expires_at < datetime.utcnow():
                return jsonify({'error': 'Invite has expired'}), 400
            
            # Create user with invited role
            user = User(
                email=data['email'],
                password_hash=hash_password(data['password']),
                full_name=data['full_name'],
                role=invite.role,
                company_id=invite.company_id
            )
            db.session.add(user)
            invite.accepted = True
            db.session.commit()
        else:
            # Create new company and admin user
            company_name = data.get('company_name', f"{data['full_name']}'s Company")
            
            company = Company(
                name=company_name,
                default_currency='INR'
            )
            db.session.add(company)
            db.session.flush()  # Get company ID
            
            user = User(
                email=data['email'],
                password_hash=hash_password(data['password']),
                full_name=data['full_name'],
                role=UserRole.ADMIN,
                company_id=company.id
            )
            db.session.add(user)
            db.session.commit()
        
        # Generate tokens
        access_token = generate_access_token(user.id, user.company_id, user.role.value)
        refresh_token = generate_refresh_token(user.id)
        
        # Set refresh token in httpOnly cookie
        response = make_response(jsonify({
            'access_token': access_token,
            'user': user.to_dict(include_company=True)
        }))
        
        # Set both refresh and access token cookies
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        return response, 201
    
    except Exception as e:
        # Log the error for debugging
        current_app.logger.error(f'Signup error: {str(e)}')
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email and password"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        if not user or not user.password_hash:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not verify_password(data['password'], user.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        # Generate tokens
        access_token = generate_access_token(user.id, user.company_id, user.role.value)
        refresh_token = generate_refresh_token(user.id)
        
        # Set refresh token in httpOnly cookie
        response = make_response(jsonify({
            'access_token': access_token,
            'user': user.to_dict(include_company=True)
        }))
        
        # Set both refresh and access token cookies
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        return response
        
    except Exception as e:
        # Log the error for debugging
        current_app.logger.error(f'Login error: {str(e)}')
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/oauth/google/callback', methods=['GET'])
def google_oauth_callback():
    """Handle Google OAuth callback redirect"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return jsonify({'error': f'OAuth error: {error}'}), 400
    
    if not code:
        return jsonify({'error': 'Authorization code required'}), 400
    
    # Exchange code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': current_app.config['GOOGLE_OAUTH_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        'redirect_uri': current_app.config['OAUTH_REDIRECT_URI'],
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Get user info
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
        
        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Create new company and admin user
            company = Company(
                name=f"{user_info.get('name', 'Company')}'s Company",
                default_currency='INR'
            )
            db.session.add(company)
            db.session.flush()
            
            user = User(
                email=user_info['email'],
                full_name=user_info.get('name', user_info['email']),
                role=UserRole.ADMIN,
                company_id=company.id,
                oauth_provider='google',
                oauth_id=user_info['id']
            )
            db.session.add(user)
            db.session.commit()
        
        # Generate our app tokens
        access_token = generate_access_token(user.id, user.company_id, user.role.value)
        refresh_token = generate_refresh_token(user.id)
        
        # Redirect directly to dashboard
        frontend_url = current_app.config['FRONTEND_ORIGIN']
        redirect_url = f"{frontend_url}/dashboard"
        
        # Set both tokens in cookies and redirect
        from flask import redirect
        response = redirect(redirect_url)
        
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        return response
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'OAuth error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@auth_bp.route('/oauth/google', methods=['POST'])
def google_oauth():
    """Exchange Google OAuth code for tokens (API endpoint)"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'Authorization code required'}), 400
    
    # Exchange code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': current_app.config['GOOGLE_OAUTH_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        'redirect_uri': current_app.config['OAUTH_REDIRECT_URI'],
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Get user info
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
        
        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Check for invite
            invite_token = data.get('invite_token')
            if invite_token:
                invite = Invite.query.filter_by(token=invite_token, accepted=False).first()
                if invite and invite.expires_at >= datetime.utcnow():
                    # Create user with invited role
                    user = User(
                        email=user_info['email'],
                        full_name=user_info.get('name', user_info['email']),
                        role=invite.role,
                        company_id=invite.company_id,
                        oauth_provider='google',
                        oauth_id=user_info['id']
                    )
                    db.session.add(user)
                    invite.accepted = True
                    db.session.commit()
                else:
                    return jsonify({'error': 'Invalid or expired invite'}), 400
            else:
                # Create new company and admin user
                company = Company(name=f"{user_info.get('name', 'Company')}'s Company", default_currency='INR')
                db.session.add(company)
                db.session.flush()
                
                user = User(
                    email=user_info['email'],
                    full_name=user_info.get('name', user_info['email']),
                    role=UserRole.ADMIN,
                    company_id=company.id,
                    oauth_provider='google',
                    oauth_id=user_info['id']
                )
                db.session.add(user)
                db.session.commit()
        
        # Generate tokens
        access_token = generate_access_token(user.id, user.company_id, user.role.value)
        refresh_token = generate_refresh_token(user.id)
        
        response = make_response(jsonify({
            'access_token': access_token,
            'user': user.to_dict(include_company=True)
        }))
        
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=current_app.config['PLATFORM'] == 'vercel',
            samesite='Lax',
            max_age=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        return response
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'OAuth error: {str(e)}'}), 400

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token using refresh token"""
    refresh_token = request.cookies.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 401
    
    # Verify refresh token
    payload = verify_token(refresh_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired refresh token'}), 401
    
    # Check if token is revoked
    token_record = RefreshToken.query.filter_by(token=refresh_token).first()
    if not token_record or token_record.revoked:
        return jsonify({'error': 'Token has been revoked'}), 401
    
    # Get user
    user = User.query.get(payload['user_id'])
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401
    
    # Generate new access token
    access_token = generate_access_token(user.id, user.company_id, user.role.value)
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict(include_company=True)
    })

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout and revoke refresh token"""
    refresh_token = request.cookies.get('refresh_token')
    
    if refresh_token:
        revoke_refresh_token(refresh_token)
    
    response = make_response(jsonify({'message': 'Logged out successfully'}))
    # Clear both tokens
    response.set_cookie('refresh_token', '', expires=0)
    response.set_cookie('access_token', '', expires=0)
    
    return response
