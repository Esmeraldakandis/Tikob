"""
TiKòb Fintech Ledger System
Double-entry immutable ledger with tax-ready allocations
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal
from models import db

class Account(db.Model):
    """Chart of accounts for double-entry bookkeeping"""
    __tablename__ = 'accounts'
    
    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint(
            type.in_(['asset', 'liability', 'equity', 'income', 'expense']),
            name='valid_account_type'
        ),
    )
    
    postings = db.relationship('LedgerPosting', back_populates='account')

class LedgerEvent(db.Model):
    """Immutable event store - never edit, only append"""
    __tablename__ = 'ledger_events'
    
    id = db.Column(db.String(50), primary_key=True)
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    ref = db.Column(db.String(100))
    meta = db.Column(db.JSON)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    postings = db.relationship('LedgerPosting', back_populates='event', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.CheckConstraint(
            event_type.in_([
                'deposit', 'withdrawal', 'interest_accrual', 
                'correction', 'payout', 'fee', 'transfer'
            ]),
            name='valid_event_type'
        ),
    )

class LedgerPosting(db.Model):
    """Double-entry postings - must always balance to zero per event"""
    __tablename__ = 'ledger_postings'
    
    id = db.Column(db.String(50), primary_key=True)
    event_id = db.Column(db.String(50), db.ForeignKey('ledger_events.id'), nullable=False)
    account_id = db.Column(db.String(50), db.ForeignKey('accounts.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    amount = db.Column(db.Numeric(18, 6), nullable=False)
    
    event = db.relationship('LedgerEvent', back_populates='postings')
    account = db.relationship('Account', back_populates='postings')

class MemberShare(db.Model):
    """Daily snapshots for time-aware interest allocation"""
    __tablename__ = 'member_shares'
    
    id = db.Column(db.String(50), primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    pool_principal = db.Column(db.Numeric(18, 6), nullable=False)
    member_principal = db.Column(db.Numeric(18, 6), nullable=False)
    member_share = db.Column(db.Numeric(18, 10), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('snapshot_date', 'member_id', 'group_id', name='unique_daily_share'),
    )

class TaxBucket(db.Model):
    """Year-to-date taxable earnings per member"""
    __tablename__ = 'tax_buckets'
    
    id = db.Column(db.String(50), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    tax_year = db.Column(db.Integer, nullable=False)
    taxable_interest = db.Column(db.Numeric(18, 6), default=0)
    total_contributions = db.Column(db.Numeric(18, 6), default=0)
    total_withdrawals = db.Column(db.Numeric(18, 6), default=0)
    last_update = db.Column(db.DateTime)
    
    __table_args__ = (
        db.UniqueConstraint('member_id', 'group_id', 'tax_year', name='unique_tax_bucket'),
    )

class TaxReport(db.Model):
    """Generated tax reports (statements, 1099-INT)"""
    __tablename__ = 'tax_reports'
    
    id = db.Column(db.String(50), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    tax_year = db.Column(db.Integer, nullable=False)
    report_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='draft')
    payload = db.Column(db.JSON)
    checksum = db.Column(db.String(64))
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finalized_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.CheckConstraint(
            report_type.in_(['statement', '1099-INT', 'summary']),
            name='valid_report_type'
        ),
        db.CheckConstraint(
            status.in_(['draft', 'final', 'corrected']),
            name='valid_report_status'
        ),
    )

STANDARD_ACCOUNTS = [
    {'id': 'pool_cash', 'type': 'asset', 'name': 'Pool Cash', 'description': 'Total cash held by savings pool'},
    {'id': 'member_principal', 'type': 'liability', 'name': 'Member Principal', 'description': 'Principal owed to members'},
    {'id': 'member_earnings', 'type': 'liability', 'name': 'Member Earnings', 'description': 'Accumulated earnings owed to members'},
    {'id': 'interest_income', 'type': 'income', 'name': 'Interest Income', 'description': 'Interest earned on pool investments'},
    {'id': 'fee_income', 'type': 'income', 'name': 'Fee Income', 'description': 'Administrative fees collected'},
    {'id': 'rounding_reserve', 'type': 'liability', 'name': 'Rounding Reserve', 'description': 'Sub-cent amounts from allocation rounding'},
    {'id': 'operating_expense', 'type': 'expense', 'name': 'Operating Expenses', 'description': 'Pool operating costs'},
]

def seed_accounts():
    """Initialize standard chart of accounts"""
    for acct_data in STANDARD_ACCOUNTS:
        existing = Account.query.get(acct_data['id'])
        if not existing:
            account = Account(**acct_data)
            db.session.add(account)
    db.session.commit()
