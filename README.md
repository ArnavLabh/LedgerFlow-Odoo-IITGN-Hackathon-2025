# LedgerFlow - Expense Management System

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

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.9+
- PostgreSQL (or use Neon)
- Git

### 1. Clone Repository

```bash
git clone <repository-url>
cd ledgerflow
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the root directory:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
JWT_SECRET=your-jwt-secret-key-change-this-in-production
FLASK_ENV=development

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/ledgerflow

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:5000/api/auth/oauth/google/callback

# CORS Configuration
FRONTEND_ORIGIN=http://localhost:5000

# Platform
PLATFORM=local

# Optional
SENTRY_DSN=
```

### 4. Initialize Database

```bash
# Initialize Alembic (first time only)
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migration
flask db upgrade
```

Or use Alembic directly:

```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 5. Seed Sample Data (Optional)

```bash
python seed_data.py
```

This creates:
- Company: "Acme Corporation"
- 4 users (Admin, CFO, Manager, Employee)
- Sample approval configuration
- 3 draft expenses

**Test Accounts**:
- Admin: `admin@acme.com` / `admin123`
- CFO: `cfo@acme.com` / `cfo123`
- Manager: `manager@acme.com` / `manager123`
- Employee: `employee@acme.com` / `employee123`

### 6. Run Development Server

```bash
python wsgi.py
```

Open http://localhost:5000

## 🚀 Deployment to Vercel

### Prerequisites

1. Vercel account
2. Vercel CLI: `npm install -g vercel`
3. PostgreSQL database (Neon recommended)

### Steps

1. **Login to Vercel**

```bash
vercel login
```

2. **Set Environment Variables**

In Vercel dashboard or via CLI:

```bash
vercel env add SECRET_KEY
vercel env add JWT_SECRET
vercel env add DATABASE_URL
vercel env add GOOGLE_OAUTH_CLIENT_ID
vercel env add GOOGLE_OAUTH_CLIENT_SECRET
vercel env add OAUTH_REDIRECT_URI
vercel env add FRONTEND_ORIGIN
```

3. **Deploy**

```bash
vercel --prod
```

4. **Run Migrations**

Connect to your Neon database and run:

```bash
alembic upgrade head
```

Or use Vercel's serverless functions to run migrations.

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

## 🧪 Testing

### Manual Testing with curl

**1. Signup**

```bash
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User",
    "company_name": "Test Company"
  }'
```

**2. Login**

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }' \
  -c cookies.txt
```

**3. Create Expense**

```bash
curl -X POST http://localhost:5000/api/expenses \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1500,
    "category": "Travel",
    "description": "Client meeting travel",
    "date_incurred": "2025-01-15"
  }'
```

**4. Submit Expense**

```bash
curl -X POST http://localhost:5000/api/expenses/<EXPENSE_ID>/submit \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**5. Approve Expense**

```bash
curl -X POST http://localhost:5000/api/approvals/<APPROVAL_ID>/decision \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "APPROVED",
    "comments": "Approved for business travel"
  }'
```

## 🏗️ Database Schema

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