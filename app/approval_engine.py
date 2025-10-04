from datetime import datetime
from app import db
from app.models import (
    Expense, Approval, ApprovalDecision, ExpenseStatus,
    ApproverAssignment, ApprovalRule, RuleType, Notification, User
)

class ApprovalEngine:
    """Handle complex approval workflows"""
    
    @staticmethod
    def create_approval_chain(expense):
        """Create approval chain when expense is submitted"""
        try:
            # Get approver assignments for this company
            assignments = ApproverAssignment.query.filter_by(
                company_id=expense.company_id
            ).order_by(ApproverAssignment.sequence).all()
            
            if not assignments:
                # No approval workflow configured, auto-approve
                expense.status = ExpenseStatus.APPROVED
                db.session.commit()
                ApprovalEngine._notify_approval_decision(expense, None, ApprovalDecision.APPROVED, auto=True)
                return
            
            # Create approval records for each step
            approvals_created = 0
            for assignment in assignments:
                approver_id = None
                
                # Handle manager assignment
                if assignment.is_manager and expense.creator.manager_id:
                    approver_id = expense.creator.manager_id
                elif assignment.user_id:
                    approver_id = assignment.user_id
                elif assignment.role:
                    # Find first user with this role in the company
                    user = User.query.filter_by(
                        company_id=expense.company_id,
                        role=assignment.role,
                        is_active=True
                    ).first()
                    if user:
                        approver_id = user.id
                
                if approver_id:
                    approval = Approval(
                        expense_id=expense.id,
                        approver_id=approver_id,
                        step=assignment.sequence,
                        decision=ApprovalDecision.PENDING
                    )
                    db.session.add(approval)
                    approvals_created += 1
            
            if approvals_created == 0:
                # No valid approvers found, auto-approve
                expense.status = ExpenseStatus.APPROVED
                db.session.commit()
                ApprovalEngine._notify_approval_decision(expense, None, ApprovalDecision.APPROVED, auto=True)
                return
            
            # Update expense status
            expense.status = ExpenseStatus.PENDING
            expense.current_approval_step = 1
            db.session.commit()
            
            # Notify first approver
            first_approval = Approval.query.filter_by(
                expense_id=expense.id,
                step=1
            ).first()
            
            if first_approval:
                ApprovalEngine._notify_approval_request(expense, first_approval.approver)
                
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create approval chain: {str(e)}")
    
    @staticmethod
    def process_approval_decision(approval, decision, comments=None):
        """Process an approval/rejection decision"""
        approval.decision = decision
        approval.comments = comments
        approval.decided_at = datetime.utcnow()
        
        expense = approval.expense
        
        # Handle rejection
        if decision == ApprovalDecision.REJECTED:
            expense.status = ExpenseStatus.REJECTED
            db.session.commit()
            ApprovalEngine._notify_approval_decision(expense, approval.approver, ApprovalDecision.REJECTED)
            return
        
        # Check conditional rules
        if ApprovalEngine._check_conditional_rules(expense):
            expense.status = ExpenseStatus.APPROVED
            db.session.commit()
            ApprovalEngine._notify_approval_decision(expense, approval.approver, ApprovalDecision.APPROVED, auto=True)
            return
        
        # Continue sequence
        next_step = approval.step + 1
        next_approval = Approval.query.filter_by(
            expense_id=expense.id,
            step=next_step
        ).first()
        
        if next_approval:
            # Move to next approver
            expense.current_approval_step = next_step
            db.session.commit()
            ApprovalEngine._notify_approval_request(expense, next_approval.approver)
        else:
            # All approvals complete
            expense.status = ExpenseStatus.APPROVED
            db.session.commit()
            ApprovalEngine._notify_approval_decision(expense, approval.approver, ApprovalDecision.APPROVED)
    
    @staticmethod
    def _check_conditional_rules(expense):
        """Check if conditional approval rules are satisfied"""
        rules = ApprovalRule.query.filter_by(
            company_id=expense.company_id,
            enabled=True
        ).all()
        
        if not rules:
            return False
        
        approvals = Approval.query.filter_by(expense_id=expense.id).all()
        total_approvers = len(approvals)
        approved_count = sum(1 for a in approvals if a.decision == ApprovalDecision.APPROVED)
        
        for rule in rules:
            # Percentage rule
            if rule.rule_type in [RuleType.PERCENTAGE, RuleType.HYBRID]:
                if rule.percentage_threshold and total_approvers > 0:
                    percentage = (approved_count / total_approvers) * 100
                    if percentage >= rule.percentage_threshold:
                        return True
            
            # Specific approver rule
            if rule.rule_type in [RuleType.SPECIFIC, RuleType.HYBRID]:
                if rule.specific_approver_user_id:
                    # Check if this specific user approved
                    specific_approval = next(
                        (a for a in approvals if a.approver_id == rule.specific_approver_user_id),
                        None
                    )
                    if specific_approval and specific_approval.decision == ApprovalDecision.APPROVED:
                        return True
                
                if rule.specific_approver_role:
                    # Check if any user with this role approved
                    for approval in approvals:
                        if (approval.approver.role == rule.specific_approver_role and
                            approval.decision == ApprovalDecision.APPROVED):
                            return True
        
        return False
    
    @staticmethod
    def _notify_approval_request(expense, approver):
        """Create notification for approval request"""
        notification = Notification(
            user_id=approver.id,
            title='New Expense Approval Request',
            message=f'{expense.creator.full_name} submitted an expense of ₹{expense.amount} for approval',
            link=f'/expenses/{expense.id}'
        )
        db.session.add(notification)
        db.session.commit()
    
    @staticmethod
    def _notify_approval_decision(expense, approver, decision, auto=False):
        """Create notification for approval decision"""
        # Notify expense creator
        if decision == ApprovalDecision.APPROVED:
            message = f'Your expense of ₹{expense.amount} has been approved'
            if auto:
                message += ' (auto-approved by conditional rule)'
        else:
            message = f'Your expense of ₹{expense.amount} has been rejected'
        
        notification = Notification(
            user_id=expense.created_by,
            title='Expense Status Update',
            message=message,
            link=f'/expenses/{expense.id}'
        )
        db.session.add(notification)
        
        # Notify company admins
        admins = User.query.filter_by(
            company_id=expense.company_id,
            role='Admin',
            is_active=True
        ).all()
        
        for admin in admins:
            if admin.id != expense.created_by:  # Don't notify if creator is admin
                admin_notification = Notification(
                    user_id=admin.id,
                    title='Expense Status Update',
                    message=f'Expense by {expense.creator.full_name} (₹{expense.amount}) has been {decision.value.lower()}',
                    link=f'/expenses/{expense.id}'
                )
                db.session.add(admin_notification)
        
        db.session.commit()