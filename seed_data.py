#!/usr/bin/env python3
"""Seed script to create sample data for LedgerFlow"""

import os
import sys
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import (
    Company, User, UserRole, Expense, ExpenseStatus,
    ApproverAssignment, ApprovalRule, RuleType
)
from app.auth import hash_password

def seed_database():
    app = create_app()
    
    with app.app_context():
        print("Creating sample data...")
        
        # Create company
        company = Company(
            name="Acme Corporation",
            default_currency="INR"
        )
        db.session.add(company)
        db.session.flush()
        
        # Create users
        admin = User(
            email="admin@acme.com",
            password_hash=hash_password("admin123"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            company_id=company.id
        )
        
        cfo = User(
            email="cfo@acme.com",
            password_hash=hash_password("cfo123"),
            full_name="CFO User",
            role=UserRole.CFO,
            company_id=company.id
        )
        
        manager = User(
            email="manager@acme.com",
            password_hash=hash_password("manager123"),
            full_name="Manager User",
            role=UserRole.MANAGER,
            company_id=company.id,
            is_manager_approver=True
        )
        
        employee = User(
            email="employee@acme.com",
            password_hash=hash_password("employee123"),
            full_name="Employee User",
            role=UserRole.EMPLOYEE,
            company_id=company.id,
            manager_id=None  # Will set after manager is created
        )
        
        db.session.add_all([admin, cfo, manager, employee])
        db.session.flush()
        
        # Set manager relationship
        employee.manager_id = manager.id
        
        # Create approver assignments
        assignment1 = ApproverAssignment(
            company_id=company.id,
            user_id=manager.id,
            sequence=1,
            is_manager=True
        )
        
        assignment2 = ApproverAssignment(
            company_id=company.id,
            user_id=cfo.id,
            sequence=2,
            is_manager=False
        )
        
        db.session.add_all([assignment1, assignment2])
        
        # Create approval rule - CFO auto-approve
        rule = ApprovalRule(
            company_id=company.id,
            rule_type=RuleType.SPECIFIC,
            specific_approver_user_id=cfo.id,
            enabled=True
        )
        db.session.add(rule)
        
        # Create sample expenses
        expense1 = Expense(
            company_id=company.id,
            created_by=employee.id,
            amount=2500.00,
            currency="INR",
            category="Travel",
            description="Flight tickets to Mumbai for client meeting",
            date_incurred=datetime.utcnow() - timedelta(days=5),
            status=ExpenseStatus.DRAFT
        )
        
        expense2 = Expense(
            company_id=company.id,
            created_by=employee.id,
            amount=850.00,
            currency="INR",
            category="Meals",
            description="Team dinner with clients",
            date_incurred=datetime.utcnow() - timedelta(days=3),
            status=ExpenseStatus.DRAFT
        )
        
        expense3 = Expense(
            company_id=company.id,
            created_by=employee.id,
            amount=15000.00,
            currency="INR",
            category="Software",
            description="Annual Jira license renewal",
            date_incurred=datetime.utcnow() - timedelta(days=1),
            status=ExpenseStatus.DRAFT
        )
        
        db.session.add_all([expense1, expense2, expense3])
        
        db.session.commit()
        
        print("✓ Sample data created successfully!")
        print("\nTest Accounts:")
        print("1. Admin:    admin@acme.com / admin123")
        print("2. CFO:      cfo@acme.com / cfo123")
        print("3. Manager:  manager@acme.com / manager123")
        print("4. Employee: employee@acme.com / employee123")
        print("\nCompany: Acme Corporation")
        print(f"\nSample expenses created: 3")

if __name__ == '__main__':
    seed_database()