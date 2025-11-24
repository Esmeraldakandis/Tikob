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
- **Premium UI/UX**: Glassmorphism design system with backdrop blur effects, animated gradient progress bars, premium typography (Poppins/Inter), AOS scroll animations, multi-step survey with smooth transitions, confetti celebrations, micro-interactions (hover/scale/glow effects), floating particles background, and fully responsive layouts.
- **Cultural Enhancements**: Integration of Haitian proverbs and financial wisdom, multi-language support (English and Haitian Creole) with a language switcher, dark mode with persistence, animated progress bars, quick actions widget, and dynamic profile avatars.
- **Global Inclusivity**: Support for various cultural savings traditions (e.g., Susu, ROSCA, Tanda) with a tradition selection during group creation.
- **Gamification**: XP system, streak tracking, reputation scoring, animated badge system (Gold, Silver, Platinum, Elite), and leaderboards to encourage engagement.
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

## Latest Updates - Premium UI/UX Overhaul (November 24, 2025)

### ✨ Glassmorphism Design System
Implemented a complete premium CSS framework (`premium.css`) with:
- **Glassmorphism Effects**: Backdrop blur, frosted glass cards with transparency and subtle borders
- **Animated Gradients**: Shimmer effects on progress bars, rotating gradient backgrounds
- **Premium Typography**: Poppins for headings (600 weight), Inter for body text (400/500 weight)
- **Color Palette**: Purple-to-pink gradients (#667eea → #764ba2), gold accents (#FFD700)
- **Floating Particles**: Animated background orbs with gradient blur effects

### 🎖️ Animated Badge & Reputation System
Redesigned `/badges` page with:
- **Reputation Scoring**: Consistency (60% weight) + Activity (40% weight) algorithm
- **Tier-Based Badges**: Gold, Silver, Platinum, and Elite with metallic gradients
- **Progress Visualization**: Animated gradient bars with shimmer effects
- **Micro-interactions**: Hover scale (1.02), glow effects, smooth transitions
- **Confetti Celebrations**: Trigger on new badge unlocks using confetti.js
- **Bug Fix**: calculate_reputation_score() now handles users with no active memberships

### 📋 Multi-Step Financial Survey
Completely redesigned `/financial-survey` with:
- **Progressive Disclosure**: One question at a time (9 questions total)
- **Smooth Transitions**: fadeSlideUp animation between steps
- **Visual Progress Bar**: Animated gradient fill showing completion percentage
- **Interactive Options**: Click-to-select cards with emojis and auto-advance
- **Form Validation**: Client-side validation ensures all questions answered
- **DOMContentLoaded Wrapper**: Prevents JavaScript timing issues
- **Confetti Success**: Celebration animation on survey completion

### 🎬 Animation Libraries Integrated
- **AOS (Animate On Scroll)**: Fade-up, fade-down, and zoom animations on scroll
- **Confetti.js**: Particle celebrations for achievements and completions
- **CSS Keyframes**: Custom animations (fadeSlideUp, shimmer, float, pulse, scaleIn)

### 🎨 Micro-Interactions Throughout
- **Hover Effects**: Scale transforms, glow shadows, opacity transitions
- **Survey Options**: Selected state with border glow and background shift
- **Buttons**: Premium gradient buttons with hover lift and shadow
- **Cards**: Glassmorphism with backdrop blur and hover depth

### 📱 Responsive Design Enhancements
- Mobile breakpoints (< 768px): Adjusted glassmorphism blur, scaled typography
- Tablet optimizations: Balanced layout for medium screens
- Desktop polish: Full glassmorphism effects with optimal performance

### 🔧 Technical Implementation
- **calculate_reputation_score()**: Early return for empty memberships prevents runtime errors
- **Context Processors**: Pass reputation data to templates globally
- **JavaScript Patterns**: DOMContentLoaded, event delegation, validation before submit
- **CSS Architecture**: Custom properties, modular class naming, performance-optimized filters

### 📊 Files Modified
- `app/static/css/premium.css`: 450+ lines of glassmorphism and animation styles
- `app/templates/badges.html`: Complete redesign with animated reputation system
- `app/templates/financial_survey.html`: Multi-step survey with progressive disclosure
- `app/templates/dashboard.html`: Immersive cards with glassmorphism and animations
- `app/templates/leaderboard.html`: 3D podium and animated rankings
- `app/templates/create_group.html`: Premium forms with SUSU duration calculator
- `app/templates/base.html`: Font imports, AOS/confetti library integrations
- `app/app.py`: Reputation scoring logic with error handling

## Additional UI/UX Improvements - Continued (November 24, 2025)

### 🏠 Dashboard Redesign
Transformed the dashboard into an immersive experience:
- **Glassmorphism Cards**: Quote, quick actions, stats, and groups all use glass effect
- **Floating Icons**: Animated stat icons (💰, 👥, 🎯) with float animation
- **Quick Actions**: Premium hover effects with translateY(-4px) and glow shadows
- **Group Cards**: Tradition icons, stat grids, role badges, progress bars
- **Empty State**: Floating icon with premium call-to-action buttons
- **Stat Cards**: Gradient text values, shimmer top border, centered layout
- **AOS Animations**: Staggered fade-up/zoom-in effects across all elements

### 🏆 Leaderboard Redesign  
Created a competitive, engaging leaderboard:
- **3D Podium**: Gold, silver, bronze bases with different heights (180px, 140px, 100px)
- **Crown Animation**: Floating crown on 1st place winner
- **User Avatars**: Gradient circular avatars with rank badges (🥇🥈🥉)
- **Animated Rankings**: Full list with hover translateX(8px) effects
- **Current User Highlight**: Special border and background for logged-in user
- **Rank Badges**: Metallic gradient backgrounds for top 3 positions
- **XP Earning Guide**: Icon cards showing how to earn XP
- **Mobile Responsive**: Podium switches to column layout on mobile

### 📝 Group Creation with SUSU Duration
Enhanced group creation form:
- **SUSU Duration Input**: Customizable cycle count (2-52 cycles)
- **Duration Calculator**: Real-time preview of estimated duration
- **Pool Estimator**: Shows total pool size (amount × cycles)
- **Premium Form Inputs**: Glassmorphism with focus states and shadows
- **Tradition Info Card**: Animated reveal with icon and description
- **Input Groups**: Styled suffix text for better UX
- **Form Hints**: Helper text for each field
- **Responsive Design**: Mobile-optimized form layout

### 🎯 Next Priorities
- Badge generation logic (Consistency, High Roller, Loyalty, Elite badges)
- Integration testing for survey submission and group creation
- Mobile responsiveness QA across all glassmorphism pages
- Accessibility audit for color contrast with backdrop blur
- UX analytics instrumentation for engagement tracking