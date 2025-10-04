#!/usr/bin/env python3
"""
Database setup and debugging script for LedgerFlow
Run this to initialize the database and check configuration
"""

import os
import sys
from app import create_app, db
from app.models import User, Company, UserRole
from app.auth import hash_password

def check_env_config():
    """Check if environment variables are properly configured"""
    print("=== Environment Configuration ===")
    
    required_vars = [
        'GOOGLE_OAUTH_CLIENT_ID',
        'GOOGLE_OAUTH_CLIENT_SECRET', 
        'DATABASE_URL',
        'SECRET_KEY',
        'JWT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
        else:
            # Mask sensitive values
            if 'SECRET' in var or 'PASSWORD' in var:
                masked_value = value[:4] + '*' * (len(value) - 4)
            elif 'CLIENT_ID' in var:
                masked_value = value[:8] + '*' * (len(value) - 8)
            else:
                masked_value = value
            print(f"✅ {var}: {masked_value}")
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment configuration.")
        return False
    else:
        print("\n✅ All required environment variables are set!")
        return True

def init_database():
    """Initialize database and run migrations"""
    print("\n=== Database Initialization ===")
    
    try:
        app = create_app()
        with app.app_context():
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Test database connection
            print("Testing database connection...")
            result = db.session.execute(db.text("SELECT 1"))
            print("✅ Database connection successful!")
            
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False

def create_test_user():
    """Create a test admin user for development"""
    print("\n=== Creating Test User ===")
    
    try:
        app = create_app()
        with app.app_context():
            # Check if admin user exists
            admin_user = User.query.filter_by(email='admin@test.com').first()
            if admin_user:
                print("✅ Test admin user already exists (admin@test.com)")
                return True
            
            # Create test company
            test_company = Company.query.filter_by(name='Test Company').first()
            if not test_company:
                test_company = Company(
                    name='Test Company',
                    default_currency='INR'
                )
                db.session.add(test_company)
                db.session.flush()
                print("✅ Test company created")
            
            # Create test admin user
            admin_user = User(
                email='admin@test.com',
                password_hash=hash_password('password123'),
                full_name='Test Admin',
                role=UserRole.ADMIN,
                company_id=test_company.id
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Test admin user created successfully!")
            print("   Email: admin@test.com")
            print("   Password: password123")
            return True
            
    except Exception as e:
        print(f"❌ Failed to create test user: {str(e)}")
        return False

def run_app_test():
    """Test if the Flask app can start properly"""
    print("\n=== Application Test ===")
    
    try:
        app = create_app()
        print("✅ Flask app created successfully!")
        
        with app.app_context():
            # Test some basic functionality
            from app.routes.auth_routes import auth_bp
            print("✅ Auth routes loaded successfully!")
            
        return True
        
    except Exception as e:
        print(f"❌ Application test failed: {str(e)}")
        return False

def main():
    """Main setup function"""
    print("🚀 LedgerFlow Database Setup & Configuration Check\n")
    
    success = True
    
    # Check environment configuration
    if not check_env_config():
        success = False
    
    # Initialize database
    if not init_database():
        success = False
    
    # Create test user
    if success and not create_test_user():
        success = False
    
    # Test application
    if success and not run_app_test():
        success = False
    
    print("\n" + "="*50)
    if success:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the server: python wsgi.py")
        print("2. Visit http://localhost:5000")
        print("3. Test login with admin@test.com / password123")
        print("4. Test Google OAuth (make sure OAuth credentials are configured)")
    else:
        print("❌ Setup completed with errors. Please fix the issues above.")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())