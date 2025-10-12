#!/usr/bin/env python3
"""
Test script to verify expense details functionality
Run this to test if the expense details page and API are working correctly
"""

import requests
import json
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_expense_detail_route():
    """Test the expense detail route directly"""
    try:
        from app import create_app
        from app.models import User, Expense, Company
        
        app = create_app()
        
        with app.test_client() as client:
            # Test the frontend route
            response = client.get('/expenses/test-id')
            print(f"Frontend route status: {response.status_code}")
            
            if response.status_code == 302:
                print("Redirected (likely to login) - this is expected without authentication")
            elif response.status_code == 200:
                print("Frontend route working correctly")
            else:
                print(f"Unexpected status code: {response.status_code}")
                
        print("✅ Expense detail route test completed")
        
    except Exception as e:
        print(f"❌ Error testing expense detail route: {e}")

def check_template_files():
    """Check if all necessary template files exist"""
    templates_to_check = [
        'app/templates/base.html',
        'app/templates/expenses/detail.html',
        'app/templates/dashboard/admin.html',
        'app/templates/dashboard/manager.html',
        'app/templates/dashboard/employee.html'
    ]
    
    for template in templates_to_check:
        if os.path.exists(template):
            print(f"✅ {template} exists")
        else:
            print(f"❌ {template} missing")

def main():
    print("Testing Expense Details Functionality")
    print("=" * 40)
    
    print("\n1. Checking template files...")
    check_template_files()
    
    print("\n2. Testing expense detail route...")
    test_expense_detail_route()
    
    print("\n" + "=" * 40)
    print("Test completed!")
    print("\nIf you see issues:")
    print("1. Make sure you have all required dependencies installed")
    print("2. Check if the database is properly configured")
    print("3. Verify that all template files exist")
    print("4. Test the application by running it and navigating to an expense detail page")

if __name__ == "__main__":
    main()