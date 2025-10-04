#!/usr/bin/env python3
"""
Check database setup and approval configuration
"""

from app import create_app, db
from app.models import Company, User, ApproverAssignment, ApprovalRule

def check_database():
    """Check if database is properly set up"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 Checking Database Setup")
        print("=" * 40)
        
        # Check companies
        companies = Company.query.all()
        print(f"Companies: {len(companies)}")
        for company in companies:
            print(f"  - {company.name} (ID: {company.id})")
        
        if not companies:
            print("❌ No companies found! Run seed_data.py first.")
            return
        
        company = companies[0]
        
        # Check users
        users = User.query.filter_by(company_id=company.id).all()
        print(f"\nUsers in {company.name}: {len(users)}")
        for user in users:
            print(f"  - {user.full_name} ({user.email}) - {user.role.value}")
        
        # Check approver assignments
        assignments = ApproverAssignment.query.filter_by(company_id=company.id).all()
        print(f"\nApprover Assignments: {len(assignments)}")
        for assignment in assignments:
            if assignment.user_id:
                user = User.query.get(assignment.user_id)
                print(f"  Step {assignment.sequence}: {user.full_name if user else 'Unknown User'}")
            elif assignment.role:
                print(f"  Step {assignment.sequence}: Role {assignment.role.value}")
            elif assignment.is_manager:
                print(f"  Step {assignment.sequence}: Manager")
        
        # Check approval rules
        rules = ApprovalRule.query.filter_by(company_id=company.id).all()
        print(f"\nApproval Rules: {len(rules)}")
        for rule in rules:
            print(f"  - {rule.rule_type.value}: {rule.percentage_threshold}% threshold" if rule.percentage_threshold else f"  - {rule.rule_type.value}")
        
        if not assignments:
            print("\n⚠️  No approval workflow configured!")
            print("   Expenses will be auto-approved.")
        
        print("\n✅ Database check completed!")

if __name__ == "__main__":
    check_database()