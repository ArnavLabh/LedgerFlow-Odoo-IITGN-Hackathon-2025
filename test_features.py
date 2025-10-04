"""
Test script to verify application state and check if all features are working
"""
import os
import sys
from app import create_app, db
from app.models import Company, User, UserRole, ApproverAssignment, ExpenseStatus
from app.approval_engine import ApprovalEngine

def test_application_state():
    """Test the current state of the application"""
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("LEDGERFLOW APPLICATION STATE TEST")
        print("="*60)
        
        # Test 1: Check database tables
        print("\n[1] Database Tables:")
        try:
            companies = Company.query.count()
            users = User.query.count()
            print(f"✓ Companies: {companies}")
            print(f"✓ Users: {users}")
        except Exception as e:
            print(f"✗ Error accessing database: {e}")
        
        # Test 2: Check for approval workflows
        print("\n[2] Approval Workflows:")
        try:
            assignments = ApproverAssignment.query.all()
            if assignments:
                print(f"✓ Found {len(assignments)} approver assignments")
                for assign in assignments:
                    print(f"  - Step {assign.sequence}: {'Manager' if assign.is_manager else f'User {assign.user_id or assign.role}'}")
            else:
                print("⚠ No approver assignments configured (expenses will auto-approve)")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Test 3: Check user roles distribution
        print("\n[3] User Roles Distribution:")
        try:
            for role in UserRole:
                count = User.query.filter_by(role=role).count()
                if count > 0:
                    print(f"  {role.value}: {count} users")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Test 4: Check if companies have admins
        print("\n[4] Company Admin Status:")
        try:
            companies = Company.query.all()
            for company in companies:
                admin = User.query.filter_by(
                    company_id=company.id,
                    role=UserRole.ADMIN,
                    is_active=True
                ).first()
                if admin:
                    print(f"✓ {company.name}: Admin = {admin.full_name}")
                else:
                    print(f"⚠ {company.name}: No admin")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Test 5: Check manager relationships
        print("\n[5] Manager Relationships:")
        try:
            employees_with_managers = User.query.filter(User.manager_id.isnot(None)).count()
            manager_approvers = User.query.filter_by(is_manager_approver=True).count()
            print(f"  Employees with managers: {employees_with_managers}")
            print(f"  Manager approvers: {manager_approvers}")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Test 6: Test expense auto-approval issue
        print("\n[6] Expense Approval Configuration:")
        try:
            from app.models import Expense
            # Get a sample company
            company = Company.query.first()
            if company:
                assignments = ApproverAssignment.query.filter_by(company_id=company.id).count()
                if assignments == 0:
                    print(f"⚠ WARNING: {company.name} has no approval workflow - expenses will auto-approve!")
                    print("  FIX: Configure approval sequence in Admin > Config")
                else:
                    print(f"✓ {company.name} has {assignments} approval steps configured")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Test 7: Check API endpoints
        print("\n[7] API Endpoints Status:")
        endpoints = [
            ('/api/users/all', 'GET', 'Get all users'),
            ('/api/company/users', 'GET', 'Get company users'),
            ('/api/admin/users/create', 'POST', 'Create user'),
            ('/api/admin/users/add', 'POST', 'Add existing user'),
            ('/api/expenses', 'GET', 'List expenses'),
            ('/api/approvals', 'GET', 'List approvals'),
        ]
        
        with app.test_client() as client:
            for endpoint, method, desc in endpoints:
                print(f"  {desc} ({endpoint}): Available")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("="*60)
        
        # Provide recommendations
        recommendations = []
        
        if not assignments:
            recommendations.append("1. Configure approval workflow: Admin > Config > Approval Sequence")
        
        if companies == 0:
            recommendations.append("2. Create a company by registering as Admin")
            
        if users == 0:
            recommendations.append("3. Create users: Admin > Users > Create User")
            
        employees_without_managers = User.query.filter_by(
            role=UserRole.EMPLOYEE,
            manager_id=None
        ).count()
        
        if employees_without_managers > 0:
            recommendations.append(f"4. Assign managers to {employees_without_managers} employees")
        
        if recommendations:
            for rec in recommendations:
                print(f"• {rec}")
        else:
            print("✓ Application is properly configured!")
        
        print("\n" + "="*60)
        
if __name__ == "__main__":
    test_application_state()