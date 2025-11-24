# TiKòb - Community Savings Group Manager

## Overview
TiKòb is a Flask-based web application designed to manage community savings groups (tontines). It enables users to create, join, and administer savings groups, facilitating transparent tracking of contributions and payouts. The project aims to empower community-based savings and lending with a user-friendly and feature-rich platform.

## User Preferences
No specific preferences documented yet.

## System Architecture

TiKòb is built with Python 3.11 and Flask 3.1.2. It uses SQLite with Flask-SQLAlchemy for database management and Jinja2 templates with Bootstrap 5 for a responsive frontend. Authentication is session-based, utilizing Werkzeug for password hashing.

**Key Features:**
- **User Management**: Signup, login, session-based authentication, and secure password handling.
- **Group Management**: Creation and joining of savings groups, viewing group details, and managing memberships.
- **Financial Tracking**: Recording contributions and payouts, maintaining a complete transaction ledger, calculating group balances, and tracking individual member contributions. Admin-only transaction entry ensures control.
- **UI/UX**: Responsive design with Bootstrap 5, clean navigation, flash messages for user feedback, and a mobile-friendly layout.
- **Cultural Enhancements**: Integration of Haitian proverbs and financial wisdom, multi-language support (English and Haitian Creole) with a language switcher, dark mode with persistence, animated progress bars, quick actions widget, and dynamic profile avatars.
- **Global Inclusivity**: Support for various cultural savings traditions (e.g., Susu, ROSCA, Tanda) with a tradition selection during group creation.
- **Gamification**: XP system, streak tracking, and leaderboards to encourage engagement.
- **Security & Performance**: CSRF protection, security headers, optimized database queries with eager loading, and comprehensive integration testing.

**Core Database Models:**
- `User`: Manages user accounts.
- `Group`: Defines savings groups with custom settings and cultural traditions.
- `Member`: Links users to groups, managing roles and activity status.
- `Transaction`: Records all financial movements (contributions, payouts).
- `Tradition`: Stores metadata for various cultural savings practices.
- `UserFinancialProfile`: Designed to capture detailed financial data for personalized recommendations.

**Design Patterns & Technical Implementations:**
- **MVC-like structure**: Separation of concerns between `app.py` (routes), `models.py` (data), and `templates/` (views).
- **Context Processors**: Used for global template functions and data (e.g., language, avatars).
- **Theming System**: CSS custom properties for dark mode, persisting preferences via LocalStorage.
- **Internationalization**: Language preferences stored in Flask sessions.
- **Dynamic Content**: Context-aware financial advice engine.

## External Dependencies
- **Flask-SQLAlchemy**: ORM for database interaction (SQLite).
- **Bootstrap 5**: Frontend framework for responsive design.
- **Werkzeug**: Used for password hashing.
- **Replit Secrets**: For storing sensitive environment variables like `SESSION_SECRET`.
- **SendGrid**: Planned for email notifications (requires API key).
- **Heroku PostgreSQL**: For production database (requires `DATABASE_URL`).
- **Exchange Rate API**: For multi-currency support (requires API key, currently uses mock data).
- **Plaid**: Bank account linking for personal money management (requires `PLAID_CLIENT_ID`, `PLAID_SECRET`).

## Recent Updates - Phase 6 Completed (November 24, 2025)

### 📊 Financial Survey & Recommendations
- **9-question survey** capturing income, savings habits, goals, risk tolerance
- **Personalized group recommendations** based on contribution comfort level
- **Smart matching algorithm** connects users with compatible savings groups
- **Financial insights engine** provides context-aware advice

### 👻 Ghost User Management
- **Placeholder members** for balanced rotation cycles
- **Lightweight User accounts** with `is_ghost` flag
- **Admin-only controls** for adding/removing ghost members
- **Security**: Ghost users cannot login or receive notifications

### 🌍 Cultural Theme Customization
- **Tradition-specific UI** with gradient headers and color schemes
- **Dynamic styling** based on selected tradition (Susu, ROSCA, Tanda, etc.)
- **Cultural context** displayed throughout group pages

### 💳 Plaid Bank Linking Foundation
- **PlaidAccount & PersonalTransaction models** for financial tracking
- **Money management dashboard** with income/expense analytics
- **Bank linking UI** ready for Plaid API configuration
- **Transaction syncing** infrastructure (requires API keys)

**Routes Added**: `/financial-survey`, `/survey-results`, `/money-management`, `/plaid/create-link-token`, `/plaid/exchange-token`, `/group/<id>/add-ghost-user`, `/group/<id>/remove-ghost/<member_id>`

**Production Note**: Requires Alembic migrations for schema changes before deploying to existing databases.