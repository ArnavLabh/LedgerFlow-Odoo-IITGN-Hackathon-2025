import uuid
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
import enum

class UserRole(enum.Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    FINANCE = "Finance"
    DIRECTOR = "Director"
    CFO = "CFO"
    EMPLOYEE = "Employee"

class ExpenseStatus(enum.Enum):
    DRAFT = "Draft"
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"

class ApprovalDecision(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class RuleType(enum.Enum):
    PERCENTAGE = "Percentage"
    SPECIFIC = "Specific"
    HYBRID = "Hybrid"

# Helper function for UUID
def generate_uuid():
    return str(uuid.uuid4())

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False, unique=True)
    default_currency = db.Column(db.String(3), nullable=False, default='INR')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', back_populates='company', lazy='dynamic')
    expenses = db.relationship('Expense', back_populates='company', lazy='dynamic')
    approver_assignments = db.relationship('ApproverAssignment', back_populates='company', lazy='dynamic')
    approval_rules = db.relationship('ApprovalRule', back_populates='company', lazy='dynamic')
    invites = db.relationship('Invite', back_populates='company', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'default_currency': self.default_currency,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth-only users
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    is_manager_approver = db.Column(db.Boolean, nullable=False, default=False)
    manager_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # Direct manager
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', etc.
    oauth_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', back_populates='users')
    expenses = db.relationship('Expense', back_populates='creator', foreign_keys='Expense.created_by')
    approvals = db.relationship('Approval', back_populates='approver', foreign_keys='Approval.approver_id')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')
    refresh_tokens = db.relationship('RefreshToken', back_populates='user', lazy='dynamic')
    subordinates = db.relationship('User', backref=db.backref('manager', remote_side=[id]))
    
    def to_dict(self, include_company=False):
        data = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'company_id': self.company_id,
            'is_manager_approver': self.is_manager_approver,
            'manager_id': self.manager_id,
            'oauth_provider': self.oauth_provider,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_company and self.company:
            data['company'] = self.company.to_dict()
        return data

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='INR')
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_incurred = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(ExpenseStatus), nullable=False, default=ExpenseStatus.DRAFT)
    current_approval_step = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', back_populates='expenses')
    creator = db.relationship('User', back_populates='expenses', foreign_keys=[created_by])
    approvals = db.relationship('Approval', back_populates='expense', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_approvals=False, include_creator=False):
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'created_by': self.created_by,
            'amount': float(self.amount),
            'currency': self.currency,
            'category': self.category,
            'description': self.description,
            'date_incurred': self.date_incurred.isoformat(),
            'status': self.status.value,
            'current_approval_step': self.current_approval_step,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_creator and self.creator:
            data['creator'] = self.creator.to_dict()
        if include_approvals:
            data['approvals'] = [a.to_dict(include_approver=True) for a in self.approvals.order_by(Approval.step).all()]
        return data

class ApproverAssignment(db.Model):
    __tablename__ = 'approver_assignments'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # Specific user
    role = db.Column(db.Enum(UserRole), nullable=True)  # Or role-based
    sequence = db.Column(db.Integer, nullable=False)
    is_manager = db.Column(db.Boolean, nullable=False, default=False)  # First approver is submitter's manager
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', back_populates='approver_assignments')
    user = db.relationship('User', foreign_keys=[user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'role': self.role.value if self.role else None,
            'sequence': self.sequence,
            'is_manager': self.is_manager,
            'created_at': self.created_at.isoformat()
        }

class Approval(db.Model):
    __tablename__ = 'approvals'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    expense_id = db.Column(db.String(36), db.ForeignKey('expenses.id'), nullable=False, index=True)
    approver_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    step = db.Column(db.Integer, nullable=False)
    decision = db.Column(db.Enum(ApprovalDecision), nullable=False, default=ApprovalDecision.PENDING)
    comments = db.Column(db.Text, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    expense = db.relationship('Expense', back_populates='approvals')
    approver = db.relationship('User', back_populates='approvals', foreign_keys=[approver_id])
    
    def to_dict(self, include_approver=False, include_expense=False):
        data = {
            'id': self.id,
            'expense_id': self.expense_id,
            'approver_id': self.approver_id,
            'step': self.step,
            'decision': self.decision.value,
            'comments': self.comments,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'created_at': self.created_at.isoformat()
        }
        if include_approver and self.approver:
            data['approver'] = self.approver.to_dict()
        if include_expense and self.expense:
            data['expense'] = self.expense.to_dict()
        return data

class ApprovalRule(db.Model):
    __tablename__ = 'approval_rules'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    rule_type = db.Column(db.Enum(RuleType), nullable=False)
    percentage_threshold = db.Column(db.Integer, nullable=True)  # For Percentage or Hybrid
    specific_approver_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)  # For Specific or Hybrid
    specific_approver_role = db.Column(db.Enum(UserRole), nullable=True)  # Alternative to user_id
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', back_populates='approval_rules')
    specific_approver_user = db.relationship('User', foreign_keys=[specific_approver_user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'rule_type': self.rule_type.value,
            'percentage_threshold': self.percentage_threshold,
            'specific_approver_user_id': self.specific_approver_user_id,
            'specific_approver_role': self.specific_approver_role.value if self.specific_approver_role else None,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)  # Frontend route
    read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='notifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'read': self.read,
            'created_at': self.created_at.isoformat()
        }

class Invite(db.Model):
    __tablename__ = 'invites'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    role = db.Column(db.Enum(UserRole), nullable=False)
    token = db.Column(db.String(100), nullable=False, unique=True, index=True)
    accepted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)  # 7 days from creation
    
    # Relationships
    company = db.relationship('Company', back_populates='invites')
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'email': self.email,
            'role': self.role.value,
            'token': self.token,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }

class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(500), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    
    # Relationships
    user = db.relationship('User', back_populates='refresh_tokens')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'expires_at': self.expires_at.isoformat(),
            'revoked': self.revoked
        }
