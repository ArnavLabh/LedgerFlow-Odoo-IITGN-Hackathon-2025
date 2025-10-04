# LedgerFlow - Expense Management System

LedgerFlow enables organizations to control and accelerate employee reimbursements by digitizing expense submission and enforcing policy-driven approvals. Managers and finance teams get real-time spend visibility and audit-ready trails, while employees receive faster decisions via automated notifications. Multi-tenant support fits multiple companies or clients in one deployment, and role-based access reduces risk by ensuring only the right approvers act. Deployed quickly on Vercel with PostgreSQL, it delivers compliance, speed, and transparency without heavy setup.

A production-ready Flask-based expense management application with multi-tenant support, complex approval workflows, and Google OAuth integration.

## 🚀 Features

- **Multi-tenant Architecture**: Support for multiple companies with isolated data
- **Role-based Access Control**: Admin, Manager, Finance, Director, CFO, Employee roles
- **Complex Approval Workflows**:
  - Sequence-based approvals
  - Conditional rules (percentage-based, specific approver, hybrid)
  - Manager assignment
- **Authentication**:
  - Email/password with JWT tokens
  - Google OAuth integration
  - Refresh tokens with httpOnly cookies
- **Real-time Notifications**: Polling-based notification system
- **Company Invite System**: Invite users via email with roles
- **Expense Management**: Create, submit, approve/reject expenses
- **Admin Configuration**: Configure approval sequences and conditional rules
- **Production-ready**: Deployable to Vercel

## 📋 Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy, Alembic
- **Database**: PostgreSQL (Neon)
- **Frontend**: Jinja templates, vanilla JavaScript, HTML/CSS
- **Authentication**: JWT, bcrypt, Google OAuth 2.0
- **Deployment**: Vercel (Python runtime)
- **Fonts**: Poppins (Google Fonts)
- **Icons**: Font Awesome 6.5

## 🎨 Design

**Color Palette**:
- Primary: `#0D5C63` (Dark Teal)
- Secondary: `#44A1A0` (Teal)
- Accent: `#78CDD7` (Light Teal)
- Background: `#FFFFFA` (Off-white)

## 📡 API Endpoints

### Authentication

- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Login
- `POST /api/auth/oauth/google` - Google OAuth
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout
- `GET /api/users/me` - Get current user

### Company

- `GET /api/company/users` - List company users
- `POST /api/company/invite` - Send invite
- `GET /api/company/invite/<token>` - Get invite details

### Expenses

- `POST /api/expenses` - Create expense
- `GET /api/expenses` - List expenses
- `GET /api/expenses/<id>` - Get expense details
- `PUT /api/expenses/<id>` - Update expense
- `DELETE /api/expenses/<id>` - Delete expense
- `POST /api/expenses/<id>/submit` - Submit for approval

### Approvals

- `GET /api/approvals/pending` - Get pending approvals
- `POST /api/approvals/<id>/decision` - Approve/reject
- `GET /api/approvals/expenses/<id>` - Get approval history

### Notifications

- `GET /api/notifications` - Get notifications
- `POST /api/notifications/mark-read` - Mark as read
- `GET /api/notifications/count` - Get unread count

### Admin

- `POST /api/admin/approver-assignments` - Set approval sequence
- `GET /api/admin/approver-assignments` - Get sequence
- `POST /api/admin/approval-rules` - Create rule
- `GET /api/admin/approval-rules` - Get rules
- `PUT /api/admin/approval-rules/<id>` - Update rule
- `DELETE /api/admin/approval-rules/<id>` - Delete rule
- `PUT /api/admin/users/<id>/role` - Update user role
- `DELETE /api/admin/users/<id>` - Deactivate user

## 🏗️ Database Schema

<img width="1806" height="1282" alt="Database Schema" src="https://github.com/user-attachments/assets/e86c30ef-6e3d-4a3e-9eb8-307db038ed40" />

### Tables

1. **companies** - Tenant/company information
2. **users** - User accounts with roles
3. **expenses** - Expense claims
4. **approver_assignments** - Approval sequence configuration
5. **approvals** - Approval records for expenses
6. **approval_rules** - Conditional approval rules
7. **notifications** - In-app notifications
8. **invites** - Company invitations
9. **refresh_tokens** - JWT refresh token management

## 📚 Key Concepts

### Approval Engine Logic

1. **Sequence-based**: Expenses go through approvers in order (Step 1, 2, 3...)
2. **Conditional Rules**:
   - **Percentage**: Auto-approve if X% of approvers approve
   - **Specific**: Auto-approve if specific user approves
   - **Hybrid**: Either condition triggers approval
3. **Manager Assignment**: First approver can be submitter's direct manager
4. **Rejection**: Any rejection stops the flow

### Notification System

- Stored in database
- Frontend polls `/api/notifications` every 10 seconds
- Notifications created for:
  - New approval requests
  - Approval decisions
  - Status changes

## 🔐 Security

- Passwords hashed with bcrypt
- JWT access tokens (15 min TTL)
- Refresh tokens in httpOnly secure cookies
- CORS configured
- SQL injection protection via SQLAlchemy
- Role-based authorization

## 📝 License

MIT License

## 👥 Contributors

Developed for Odoo x IITGN Hackathon 2025

## 🆘 Support

For issues or questions, please create an issue in the repository.

---

**Built using Flask, SQLAlchemy, and modern web technologies**
