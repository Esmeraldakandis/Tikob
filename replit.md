# TiKòb - Community Savings Group Manager

## Overview
TiKòb is a Flask-based web application for managing community savings groups (tontines). It allows users to create or join savings groups, track contributions and payouts, and manage group members.

**Current State**: MVP completed with all core features functional
**Last Updated**: November 24, 2025

## Purpose
- Enable users to create and manage savings groups
- Track member contributions and payouts
- Provide transparent ledger system for group finances
- Facilitate community-based savings and lending

## Project Architecture

### Technology Stack
- **Backend**: Python 3.11, Flask 3.1.2
- **Database**: SQLite with Flask-SQLAlchemy ORM
- **Frontend**: HTML5, Jinja2 templates, Bootstrap 5
- **Authentication**: Session-based with Werkzeug password hashing

### Project Structure
```
/app
  ├── app.py              # Main Flask application with routes
  ├── models.py           # Database models (User, Group, Member, Transaction)
  ├── tikob.db           # SQLite database (auto-created)
  ├── templates/         # HTML templates
  │   ├── base.html      # Base template with navigation
  │   ├── login.html     # User login page
  │   ├── signup.html    # User registration page
  │   ├── dashboard.html # User dashboard showing all groups
  │   ├── create_group.html # Create new savings group
  │   ├── join_group.html    # Join existing group
  │   ├── group_detail.html  # Group information and members
  │   └── ledger.html        # Transaction ledger
  └── static/
      └── css/
          └── style.css  # Custom styling
```

### Database Models
1. **User**: User accounts (username, email, password_hash)
2. **Group**: Savings groups (name, contribution amount/frequency, group code)
3. **Member**: User-Group relationships (role: admin/member, active status)
4. **Transaction**: Financial records (contributions/payouts with amounts)

## MVP Features Implemented

### User Management
- ✅ User signup and login
- ✅ Session-based authentication
- ✅ Password hashing with Werkzeug
- ✅ Logout functionality

### Group Management
- ✅ Create new savings groups with custom settings
- ✅ Join groups using unique group codes
- ✅ View all groups on dashboard
- ✅ Group details page with member list
- ✅ Leave/unsubscribe from groups

### Financial Tracking
- ✅ Record contributions (money in)
- ✅ Record payouts (money out)
- ✅ Transaction ledger with complete history
- ✅ Group balance calculation
- ✅ Per-member contribution tracking
- ✅ Admin-only transaction entry

### User Interface
- ✅ Bootstrap 5 responsive design
- ✅ Clean navigation with user context
- ✅ Flash messages for user feedback
- ✅ Mobile-friendly layout
- ✅ Custom CSS styling

## Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Redirect to dashboard or login |
| `/signup` | GET, POST | User registration |
| `/login` | GET, POST | User authentication |
| `/logout` | GET | End user session |
| `/dashboard` | GET | View all user's groups |
| `/create-group` | GET, POST | Create new savings group |
| `/join-group` | GET, POST | Join group with code |
| `/group/<id>` | GET | View group details |
| `/group/<id>/ledger` | GET | View transaction ledger |
| `/group/<id>/add-transaction` | POST | Record new transaction |
| `/group/<id>/unsubscribe` | POST | Leave group |

## Environment Variables
- `SESSION_SECRET`: Flask session secret key (stored in Replit Secrets)

## Running the Application
The app runs automatically via the configured workflow:
```bash
cd app && python app.py
```
- Accessible at: `http://0.0.0.0:5000`
- Debug mode enabled for development

## Recent Changes (November 24, 2025)
- Initial project setup with Flask and SQLAlchemy
- Created all database models with proper relationships
- Implemented complete authentication system
- Built all MVP features for group and transaction management
- Added Bootstrap UI with custom styling
- Configured workflow for automatic server startup

## User Preferences
- No specific preferences documented yet

## Next Phase Features (Planned)
1. Contribution reminders and notifications
2. Admin approval system for members and transactions
3. Financial reports and export functionality
4. Payment verification with receipt uploads
5. User profile management and payment history
