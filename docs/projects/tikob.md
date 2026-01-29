# TiKòb — Project Brief and High-Level Context

## Audience: Senior Architects, Product Managers, Principal Engineers.

### Executive summary
TiKòb is a production-grade fintech platform that digitizes traditional community savings practices (SUSU, Tontine, ROSCA, Chama, Pardna, etc.) with a culturally-led product design rooted in the Haitian Lakou. The platform blends a bank-grade double-entry ledger, precision financial computations, regulatory-grade tax reporting, and modern integrations (Plaid, Google Gemini AI) to serve global community savings groups.

### Goals
- Provide immutable, auditable financial records for community groups.
- Preserve cultural practices with accessible UX and multilingual support.
- Operate with financial accuracy (banker’s rounding) and regulatory readiness (1099-INT style tax reporting).
- Enable bank account linking for reliable fund movements while maintaining privacy and security.

### Primary stakeholders
- Community members and group administrators (end users)
- Product & design (cultural UX and gamification)
- Engineering (backend ledger, integrations, infra)
- Compliance & finance (tax reporting, audit)
- Operations (security, deployment, monitoring)

### Key capabilities (extracted from README)
- Double-entry ledger system with immutable event sourcing and ledger events/postings.
- Decimal precision using ROUND_HALF_EVEN for financial correctness.
- Time-weighted interest allocation and TaxBucket / TaxReport generation (1099-INT).
- Plaid integration for bank linking; AI translations via Google Gemini for multilingual support.
- Cultural design system (Lakou), gamification (XP, badges, streaks), and multi-language support (12 languages).

### Constraints and non-functional requirements
- Accuracy: Financial calculations must use fixed decimal arithmetic with banker’s rounding.
- Auditability: All financial actions recorded as immutable LedgerEvent objects.
- Security: Strict authentication protections, rate limiting, CSRF, secure headers.
- Licensing: AGPL-3.0 imposes source-sharing obligations when running TiKòb as a service.
- Operability: Must be testable with Pytest and integrate with PostgreSQL / SQLAlchemy in production environments.

### Repository pointers (structure reference)
- app/app.py — Flask application entry
- app/models.py — SQLAlchemy data models
- app/ledger_service.py — Double-entry bookkeeping logic
- app/ai_service.py — AI translation and proverb generation
- app/tests/test_ledger.py — Financial logic tests

### Usage guidance for architects
- Treat the ledger_service and LedgerEvent model as the trust boundary for financial state changes.
- Plan integration contracts (Plaid, SendGrid, Gemini AI) as isolated ports; protect keys and limit blast radius via token-scoped access.
- Ensure time-weighted interest allocation processes are reproducible and can be re-run deterministically for audits.