#!/usr/bin/env python3
"""
Test script to debug expense submission issues
Run this script to test the expense API endpoints
"""

import requests
import json
from datetime import datetime, date

# Configuration
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "admin@acme.com"
TEST_PASSWORD = "admin123"

def test_expense_submission():
    """Test the complete expense submission flow"""
    
    print("🧪 Testing Expense Submission Flow")
    print("=" * 50)
    
    # Step 1: Login
    print("1. Logging in...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        print(f"   Login Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Login failed: {response.text}")
            return
        
        auth_data = response.json()
        access_token = auth_data.get('access_token')
        print(f"   ✅ Login successful")
        
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return
    
    # Step 2: Create expense
    print("\n2. Creating expense...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    expense_data = {
        "amount": 1500.00,
        "category": "Travel",
        "description": "Test expense for debugging",
        "date_incurred": date.today().isoformat(),
        "currency": "INR"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/expenses", json=expense_data, headers=headers)
        print(f"   Create Status: {response.status_code}")
        
        if response.status_code != 201:
            print(f"   Create failed: {response.text}")
            return
        
        expense = response.json()
        expense_id = expense.get('id')
        print(f"   ✅ Expense created with ID: {expense_id}")
        print(f"   Status: {expense.get('status')}")
        
    except Exception as e:
        print(f"   ❌ Create error: {e}")
        return
    
    # Step 3: Submit for approval
    print("\n3. Submitting for approval...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/expenses/{expense_id}/submit", headers=headers)
        print(f"   Submit Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Submit failed: {response.text}")
            return
        
        updated_expense = response.json()
        print(f"   ✅ Expense submitted successfully")
        print(f"   New Status: {updated_expense.get('status')}")
        print(f"   Approval Step: {updated_expense.get('current_approval_step')}")
        
        if 'approvals' in updated_expense:
            print(f"   Approvals created: {len(updated_expense['approvals'])}")
        
    except Exception as e:
        print(f"   ❌ Submit error: {e}")
        return
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_expense_submission()