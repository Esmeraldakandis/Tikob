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

## Phase 4: Beta Features Implementation (Completed - November 24, 2025)
- ✅ Created database models for XP tracking, streaks, challenges, financial goals, personalized advice
- ✅ Implemented XP service with award_xp, update_streak, get_user_rank functions
- ✅ Built dynamic financial advice engine with context-aware recommendations
- ✅ Created multi-currency support with 7 currencies (USD, EUR, GBP, HTG, NGN, KES, GHS)
- ✅ Added leaderboard route with top 50 users ranked by total XP
- ✅ Integrated XP/streak tracking into transaction creation with enhanced feedback
- ✅ Email notifications for contributions, approvals, and badge achievements

## Production Deployment Checklist
1. **Database Migration**: Run `flask db upgrade` on Heroku to create beta feature tables
2. **Environment Variables**: Set SESSION_SECRET, DATABASE_URL, SENDGRID_API_KEY, FROM_EMAIL
3. **SendGrid Setup**: Use Replit's SendGrid connector for email notifications
4. **Exchange Rates**: Set EXCHANGE_RATE_API_KEY or use mock rates (already initialized)
5. **Heroku Commands**:
   ```bash
   heroku create your-app-name
   heroku addons:create heroku-postgresql:essential-0
   git push heroku main
   heroku run flask db upgrade
   heroku config:set SESSION_SECRET=your-secret-key
   heroku config:set FLASK_ENV=production
   ```

## Beta Features Status
**Implemented & Functional:**
- XP System: Users earn 10 XP per contribution + streak bonuses
- Streak Tracking: Daily streak counter with longest streak record
- Leaderboard: Top 50 users by XP with medals for top 3
- Dynamic Advice: Context-aware financial tips based on savings patterns
- Multi-Currency: Support for 7 currencies with conversion utilities
- Challenges: Database schema ready (UI pending)
- Financial Goals: Database schema ready (UI pending)

**Testing Status:**
- Core features: 9/9 tests passing
- Beta features: Infrastructure complete, tests pending
- Email notifications: Integrated, SendGrid API key required

**Known Limitations:**
- Exchange rates use mock data (API integration requires EXCHANGE_RATE_API_KEY)
- Challenge/Goal UI not yet implemented (backend complete)
- Leaderboard navigation link not added to base.html
- Beta feature migrations require fresh database or manual migration
