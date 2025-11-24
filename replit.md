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