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

### Phase 1: MVP Completion
- Initial project setup with Flask and SQLAlchemy
- Created all database models with proper relationships
- Implemented complete authentication system
- Built all MVP features for group and transaction management
- Added Bootstrap UI with custom styling
- Configured workflow for automatic server startup

### Phase 2: Enhancements & Production Readiness
- Applied luxury branding with navy/gold/cream palette and Playfair Display typography
- Implemented admin approval workflow for new members
- Added receipt upload functionality with security validation (file type, size limits, secure filenames)
- Integrated rewards/badges system with 6 achievement levels
- Created financial advice module with rotating tips and motivational quotes
- Built admin dashboard for managing pending member approvals
- Added receipt retention policy with automatic cleanup (90-day retention)

### Phase 3: Security & Performance (Completed - November 24, 2025)
- ✅ Added CSRF protection with Flask-WTF to all 11 POST forms (login, signup, create/join group, transactions, approvals, cleanup, unsubscribe)
- ✅ Implemented security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS)
- ✅ Fixed N+1 query issues in dashboard (member stats), group_detail (contribution totals), and ledger (transactions)
- ✅ Optimized database queries with eager loading (joinedload/selectinload) and aggregate queries
- ✅ Created comprehensive integration test suite (approval workflow, badge awarding, file uploads)
- ✅ Documented Heroku deployment strategy with PostgreSQL migration, environment variables, backup scripts
- ✅ Designed beta features in BETA_FEATURES.md: dynamic financial advice, multi-currency support, gamified rewards

## User Preferences
- No specific preferences documented yet

## Production Deployment
- See `DEPLOYMENT_GUIDE.md` for complete Heroku deployment instructions
- Environment variables: SESSION_SECRET, DATABASE_URL, FLASK_ENV
- Database backup strategy: Automated daily backups with Heroku Postgres
- Performance optimizations: Connection pooling, query optimization, eager loading
- Security: CSRF protection, security headers, file upload validation, password hashing

## Beta Features (Planned - Phase 4)
See `docs/BETA_FEATURES.md` for detailed technical designs:
1. **Dynamic Financial Advice System**: Personalized, context-aware advice based on user behavior and goals
2. **Multi-Currency Support**: Real-time exchange rates, per-member currency preferences, automatic conversions
3. **Gamified Rewards Enhancement**: XP system, streak tracking, challenges, leaderboards, social features

## Technical Debt & Future Improvements
1. Fix integration test fixtures (SQLAlchemy session DetachedInstanceError - infrastructure complete, needs fixture refactoring)
2. Add rate limiting with Flask-Limiter (protect against brute force attacks)
3. Implement email notifications with SendGrid (member approvals, transaction alerts)
4. Add session timeout configuration (security best practice)
5. Set up CI/CD pipeline with GitHub Actions (automated testing and deployment)
6. Implement feature flags for gradual rollouts (beta features)
7. Add analytics tracking with Google Analytics or Mixpanel
8. Create staging environment for testing
9. Add database indexes for frequently queried fields (user.username, group.group_code, transaction.created_at)
10. Implement caching layer with Redis for leaderboards/dashboards

## Phase 4: Production Launch (Next Steps)
1. Fix test fixtures and run full test suite
2. Deploy to Heroku following DEPLOYMENT_GUIDE.md
3. Configure production PostgreSQL and environment variables
4. Set up automated database backups
5. Implement rate limiting and session timeout
6. Add email notifications for critical events
7. Set up monitoring and analytics
8. Create staging environment
9. Begin beta feature implementation (see docs/BETA_FEATURES.md)
