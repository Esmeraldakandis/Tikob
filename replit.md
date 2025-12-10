# TiKòb - Community Savings Group Manager

## Overview
TiKòb is a Flask-based web application designed to manage community savings groups (tontines). It enables users to create, join, and administer savings groups, facilitating transparent tracking of contributions and payouts. The project aims to empower community-based savings and lending with a user-friendly and feature-rich platform, incorporating cultural financial wisdom and gamification to enhance engagement. It features a professional-grade double-entry bookkeeping system for robust financial tracking, including time-weighted interest allocation and tax reporting capabilities.

## User Preferences
- **License**: AGPL-3.0 chosen for protection against competitors taking code without contributing back

## System Architecture
TiKòb is built with Python 3.11 and Flask 3.1.2, using SQLite with Flask-SQLAlchemy for the database and Jinja2 templates with Bootstrap 5 for the frontend. Authentication is session-based.

**Key Features:**
- **User & Group Management**: Secure user accounts, group creation, joining, and membership administration.
- **Financial Tracking**: Comprehensive transaction ledger with double-entry bookkeeping, immutable event sourcing, decimal precision, and reconciliation services. This includes tracking contributions, payouts, and time-weighted interest allocation.
- **Impact Visualizer Dashboard**: Animated dashboard with 3D metric cards, global community map visualization, savings milestones with confetti/fireworks celebrations, streak tracking, and user statistics. Fully responsive and localized.
- **Premium UI/UX**: Glassmorphism design system, animated gradients, premium typography, AOS scroll animations, micro-interactions, floating particles background, and fully responsive layouts.
- **Cultural & Global Inclusivity**: Integration of Haitian proverbs, multi-language support (English/Haitian Creole), dark mode, and support for various cultural savings traditions (e.g., Susu, ROSCA, Tanda).
- **Gamification**: XP system, streak tracking, reputation scoring, an animated tier-based badge system (Gold, Silver, Platinum, Elite), and leaderboards.
- **Personalized Recommendations**: A multi-step financial survey generates personalized group recommendations and financial insights.
- **Security & Performance**: CSRF protection, security headers, login blocking after 5 failed attempts, optimized database queries, and comprehensive integration testing.

**Core Database Models:**
- `User`: Manages user accounts.
- `Group`: Defines savings groups with custom settings and cultural traditions.
- `Member`: Links users to groups, managing roles and activity status.
- `Transaction`: Records financial movements.
- `Tradition`: Stores metadata for cultural savings practices.
- `UserFinancialProfile`: Captures detailed financial data.
- `Ledger Models`: Includes `Account`, `LedgerEvent`, `LedgerPosting`, `MemberShare`, `TaxBucket`, `TaxReport` for the double-entry system.
- `PlaidAccount` & `PersonalTransaction`: For future bank linking and personal money management.

**Design Patterns & Technical Implementations:**
- **MVC-like structure**: Separation of concerns for routes, data models, and templates.
- **Context Processors**: For global template functions and data.
- **Theming System**: CSS custom properties for dark mode, persisting preferences via LocalStorage.
- **Internationalization**: Language preferences stored in Flask sessions.
- **Dynamic Content**: Context-aware financial advice engine and culturally themed UI customization.
- **Advanced Badge Criteria**: Badges awarded based on total contributions, group count, streak, high contribution, loyalty, and reputation.
- **Immersive Animation System** (immersive.css): CSS-only motion design with floating particles, parallax effects, depth shadows, interactive card tilts, spring physics animations, and orbiting profile badges. Includes comprehensive dark mode overrides for all components.

## External Dependencies
- **Flask-SQLAlchemy**: ORM for database interaction (SQLite for development, Heroku PostgreSQL for production).
- **Bootstrap 5**: Frontend framework.
- **Werkzeug**: For password hashing.
- **Replit Secrets**: For sensitive environment variables (`SESSION_SECRET`).
- **SendGrid**: For email notifications (planned).
- **Exchange Rate API**: For multi-currency support (currently uses mock data).
- **Bank Linking**: Plaid integration exists but is optional. **Recommended alternative: Teller** (teller.io) - simpler API, modern approach, competitive pricing for US bank coverage. Other options: Finexer (90% cheaper, UK/EU), TrueLayer (EU).