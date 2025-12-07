# TiKòb - Global Community Savings Platform

<div align="center">
  <img src="app/static/images/haiti-emblem.svg" alt="TiKòb Logo" width="120">
  
  **L'Union Fait La Force** — *Unity Makes Strength*
  
  *A fintech-grade platform for managing community savings groups worldwide*
  
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
  [![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com)
  [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
</div>

---

## Overview

**TiKòb** is a production-ready fintech application that digitizes traditional community savings groups known as SUSU, Tontine, ROSCA, Chama, Pardna, and other cultural savings traditions practiced by millions worldwide.

Built with a beautiful **Haitian "Lakou" design aesthetic**, TiKòb combines cultural heritage with modern financial technology to create an immersive, trustworthy platform for community-based savings and lending.

## Key Features

### Financial Infrastructure
- **Double-Entry Ledger System** - Bank-grade accounting with immutable event sourcing
- **Decimal Precision** - Banker's rounding (ROUND_HALF_EVEN) for financial accuracy
- **Tax Reporting** - Automatic 1099-INT generation for interest earnings
- **Time-Weighted Interest Allocation** - Fair distribution of earnings based on contribution timing
- **Plaid Integration** - Bank account linking for seamless transactions

### Cultural & Global Inclusivity
- **12 Language Support** - English, Haitian Creole, Spanish, French, Portuguese, Arabic, Chinese, Hindi, Japanese, Korean, Russian, German
- **AI-Powered Translations** - Accurate translations via Google Gemini AI
- **10+ Cultural Traditions** - Support for Susu, ROSCA, Tontine, Chama, Tandas, Pardna, Hagbad, Hui, Gameya, and Ekub
- **Real-Time Haitian Proverbs** - AI-generated authentic Creole wisdom

### Beautiful Lakou Design System
- **Warm Haitian Color Palette** - Mahogany, mango, Caribbean blue, palm green
- **Cultural Typography** - DM Serif Display + Source Sans Pro
- **Detailed Haitian Coat of Arms** - Palm tree, flags, drums, cannons, "L'Union Fait La Force" motto
- **Light/Dark Mode** - Full theme support with smooth transitions
- **Glassmorphism Effects** - Modern, immersive UI experience

### Gamification & Engagement
- **XP System** - Earn experience for contributions and activity
- **Achievement Badges** - Gold, Silver, Platinum, Elite tiers
- **Streak Tracking** - Maintain contribution consistency
- **Reputation Scoring** - Build trust within the community
- **Leaderboards** - Celebrate top contributors

### Security
- **Login Protection** - 5-attempt blocking with 15-minute cooldown
- **CSRF Protection** - Flask-WTF integration
- **Security Headers** - Flask-Talisman implementation
- **Rate Limiting** - Request throttling via Flask-Limiter
- **Password Hashing** - Werkzeug security utilities

## Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python 3.11, Flask 3.1.2 |
| **Database** | PostgreSQL (SQLAlchemy ORM) |
| **Frontend** | Jinja2, Bootstrap 5, CSS3 |
| **AI** | Google Gemini AI |
| **Banking** | Plaid API |
| **Email** | SendGrid |
| **Testing** | Pytest (37 comprehensive tests) |

## Project Structure

```
tikob/
├── app/
│   ├── app.py              # Main Flask application
│   ├── models.py           # SQLAlchemy models
│   ├── ledger_service.py   # Double-entry bookkeeping
│   ├── ai_service.py       # Gemini AI integration
│   ├── static/
│   │   ├── css/
│   │   │   ├── lakou.css   # Cultural design system
│   │   │   └── premium.css # Glassmorphism effects
│   │   └── images/
│   │       └── haiti-emblem.svg
│   ├── templates/          # Jinja2 templates
│   └── tests/
│       └── test_ledger.py  # Financial logic tests
└── README.md
```

## Core Database Models

- **User** - Account management with reputation and XP
- **Group** - Savings groups with cultural themes
- **Member** - User-to-group relationships with roles
- **Transaction** - Financial movement records
- **Account** - Ledger accounts (Asset, Liability, Equity, Revenue, Expense)
- **LedgerEvent** - Immutable financial events
- **LedgerPosting** - Double-entry postings
- **TaxBucket** - Interest allocation tracking
- **TaxReport** - 1099-INT generation

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Plaid API credentials (optional, for bank linking)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tikob.git
cd tikob

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SESSION_SECRET=your-secret-key
export DATABASE_URL=your-postgres-url

# Run the application
cd app && python app.py
```

### Running Tests

```bash
pytest app/tests/ -v
```

## Cultural Inspiration

TiKòb is inspired by the **Lakou** tradition - the communal courtyard that was the heart of Haitian village life. Just as families gathered in the lakou to share resources and support each other, TiKòb creates a digital space for communities worldwide to practice collective savings.

> *"Mennen chèn ki kase yo"* — *Unite the broken chains*

## Roadmap

- [ ] Impact Visualizer Dashboard with animated contribution maps
- [ ] ACH payment processing via Plaid
- [ ] Mobile-responsive progressive web app
- [ ] Group chat and notifications
- [ ] Multi-currency support with live exchange rates

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <strong>Built with love for communities worldwide</strong>
  <br>
  <em>Ansanm nou pi fò — Together we are stronger</em>
</div>
