"""
TiKòb Ledger Service
Double-entry posting with validation, reconciliation, and tax allocation
"""
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional, Dict
import uuid
import hashlib
import json

from models import db, User, Group, Member
from ledger_models import (
    Account, LedgerEvent, LedgerPosting, 
    MemberShare, TaxBucket, TaxReport, seed_accounts
)

PRECISION = Decimal('0.000001')
CURRENCY_PRECISION = Decimal('0.01')

def generate_id(prefix: str = '') -> str:
    """Generate unique ID with optional prefix"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"

def bankers_round(x: Decimal, places: int = 2) -> Decimal:
    """Round using banker's rounding (round half to even)"""
    q = Decimal(10) ** -places
    return x.quantize(q, rounding=ROUND_HALF_EVEN)

class LedgerError(Exception):
    """Custom exception for ledger operations"""
    pass

class LedgerService:
    """Core ledger operations with double-entry validation"""
    
    @staticmethod
    def validate_postings_balance(postings: List[Tuple[str, Decimal]]) -> bool:
        """Verify postings sum to zero"""
        total = sum(p[1] for p in postings)
        return total == Decimal('0')
    
    @staticmethod
    def create_event(
        event_type: str,
        ref: str,
        meta: dict,
        group_id: int = None,
        created_by: int = None
    ) -> LedgerEvent:
        """Create immutable ledger event"""
        event = LedgerEvent(
            id=generate_id('evt_'),
            ts=datetime.utcnow(),
            event_type=event_type,
            ref=ref,
            meta=meta,
            group_id=group_id,
            created_by=created_by
        )
        db.session.add(event)
        return event
    
    @staticmethod
    def post_entries(
        event: LedgerEvent,
        entries: List[Tuple[str, int, Decimal, int]]
    ) -> List[LedgerPosting]:
        """
        Post multiple ledger entries for an event
        entries: [(account_id, member_id, amount, group_id), ...]
        """
        postings = []
        total = Decimal('0')
        
        for account_id, member_id, amount, group_id in entries:
            posting = LedgerPosting(
                id=generate_id('post_'),
                event_id=event.id,
                account_id=account_id,
                member_id=member_id,
                group_id=group_id,
                amount=amount
            )
            db.session.add(posting)
            postings.append(posting)
            total += amount
        
        if total != Decimal('0'):
            raise LedgerError(f"Postings do not balance: {total}")
        
        return postings
    
    @staticmethod
    def record_deposit(
        member_id: int,
        group_id: int,
        amount: Decimal,
        ref: str,
        created_by: int = None
    ) -> LedgerEvent:
        """Record member deposit with double-entry"""
        amount = Decimal(str(amount))
        
        meta = {
            'member_id': member_id,
            'group_id': group_id,
            'amount': str(amount),
            'action': 'deposit'
        }
        
        event = LedgerService.create_event(
            'deposit', ref, meta, group_id, created_by
        )
        
        entries = [
            ('pool_cash', member_id, amount, group_id),
            ('member_principal', member_id, -amount, group_id),
        ]
        
        LedgerService.post_entries(event, entries)
        LedgerService.update_share_snapshot(member_id, group_id)
        LedgerService.update_tax_bucket_contribution(member_id, group_id, amount)
        
        db.session.commit()
        return event
    
    @staticmethod
    def record_withdrawal(
        member_id: int,
        group_id: int,
        amount: Decimal,
        ref: str,
        created_by: int = None
    ) -> LedgerEvent:
        """Record member withdrawal with double-entry"""
        amount = Decimal(str(amount))
        
        available = LedgerService.get_member_principal(member_id, group_id)
        if amount > available:
            raise LedgerError(f"Insufficient funds: {amount} > {available}")
        
        meta = {
            'member_id': member_id,
            'group_id': group_id,
            'amount': str(amount),
            'action': 'withdrawal'
        }
        
        event = LedgerService.create_event(
            'withdrawal', ref, meta, group_id, created_by
        )
        
        entries = [
            ('pool_cash', member_id, -amount, group_id),
            ('member_principal', member_id, amount, group_id),
        ]
        
        LedgerService.post_entries(event, entries)
        LedgerService.update_share_snapshot(member_id, group_id)
        LedgerService.update_tax_bucket_withdrawal(member_id, group_id, amount)
        
        db.session.commit()
        return event
    
    @staticmethod
    def accrue_interest(
        group_id: int,
        accrual_date: date,
        total_interest: Decimal,
        ref: str
    ) -> LedgerEvent:
        """
        Allocate interest across members using D-1 share snapshots
        Uses time-aware allocation to prevent timing arbitrage
        """
        total_interest = Decimal(str(total_interest))
        prior_date = accrual_date - timedelta(days=1)
        
        shares = MemberShare.query.filter_by(
            group_id=group_id,
            snapshot_date=prior_date
        ).all()
        
        if not shares:
            shares = LedgerService.generate_share_snapshots(group_id, prior_date)
        
        meta = {
            'group_id': group_id,
            'accrual_date': str(accrual_date),
            'total_interest': str(total_interest),
            'share_count': len(shares),
            'snapshot_date': str(prior_date)
        }
        
        event = LedgerService.create_event(
            'interest_accrual', ref, meta, group_id
        )
        
        entries = []
        allocations = []
        total_allocated = Decimal('0')
        
        for share in shares:
            alloc = (total_interest * Decimal(str(share.member_share))).quantize(PRECISION)
            allocations.append((share.member_id, alloc))
            total_allocated += alloc
            
            entries.append(('interest_income', None, -alloc, group_id))
            entries.append(('member_earnings', share.member_id, alloc, group_id))
        
        remainder = total_interest - total_allocated
        if remainder != Decimal('0'):
            entries.append(('interest_income', None, -remainder, group_id))
            entries.append(('rounding_reserve', None, remainder, group_id))
        
        LedgerService.post_entries(event, entries)
        
        tax_year = accrual_date.year
        for member_id, alloc in allocations:
            rounded_alloc = bankers_round(alloc)
            LedgerService.update_tax_bucket_interest(member_id, group_id, rounded_alloc, tax_year)
        
        db.session.commit()
        return event
    
    @staticmethod
    def get_member_principal(member_id: int, group_id: int) -> Decimal:
        """Get current principal balance for member"""
        result = db.session.query(
            db.func.coalesce(db.func.sum(LedgerPosting.amount), 0)
        ).filter(
            LedgerPosting.account_id == 'member_principal',
            LedgerPosting.member_id == member_id,
            LedgerPosting.group_id == group_id
        ).scalar()
        
        return abs(Decimal(str(result or 0)))
    
    @staticmethod
    def get_member_earnings(member_id: int, group_id: int) -> Decimal:
        """Get accumulated earnings for member"""
        result = db.session.query(
            db.func.coalesce(db.func.sum(LedgerPosting.amount), 0)
        ).filter(
            LedgerPosting.account_id == 'member_earnings',
            LedgerPosting.member_id == member_id,
            LedgerPosting.group_id == group_id
        ).scalar()
        
        return Decimal(str(result or 0))
    
    @staticmethod
    def get_member_position(member_id: int, group_id: int) -> Dict:
        """Get complete member financial position"""
        principal = LedgerService.get_member_principal(member_id, group_id)
        earnings = LedgerService.get_member_earnings(member_id, group_id)
        
        tax_year = datetime.utcnow().year
        bucket = TaxBucket.query.filter_by(
            member_id=member_id,
            group_id=group_id,
            tax_year=tax_year
        ).first()
        
        return {
            'principal': float(principal),
            'earnings': float(earnings),
            'total_balance': float(principal + earnings),
            'taxable_ytd': float(bucket.taxable_interest) if bucket else 0,
            'contributions_ytd': float(bucket.total_contributions) if bucket else 0,
            'withdrawals_ytd': float(bucket.total_withdrawals) if bucket else 0,
        }
    
    @staticmethod
    def get_pool_balance(group_id: int) -> Decimal:
        """Get total pool cash balance"""
        result = db.session.query(
            db.func.coalesce(db.func.sum(LedgerPosting.amount), 0)
        ).filter(
            LedgerPosting.account_id == 'pool_cash',
            LedgerPosting.group_id == group_id
        ).scalar()
        
        return Decimal(str(result or 0))
    
    @staticmethod
    def update_share_snapshot(member_id: int, group_id: int) -> MemberShare:
        """Update member's share snapshot for today"""
        today = date.today()
        
        pool_principal = LedgerService.get_pool_balance(group_id)
        member_principal = LedgerService.get_member_principal(member_id, group_id)
        
        if pool_principal > 0:
            share = member_principal / pool_principal
        else:
            share = Decimal('0')
        
        existing = MemberShare.query.filter_by(
            snapshot_date=today,
            member_id=member_id,
            group_id=group_id
        ).first()
        
        if existing:
            existing.pool_principal = pool_principal
            existing.member_principal = member_principal
            existing.member_share = share
            return existing
        
        snapshot = MemberShare(
            id=generate_id('share_'),
            snapshot_date=today,
            member_id=member_id,
            group_id=group_id,
            pool_principal=pool_principal,
            member_principal=member_principal,
            member_share=share
        )
        db.session.add(snapshot)
        return snapshot
    
    @staticmethod
    def generate_share_snapshots(group_id: int, snapshot_date: date) -> List[MemberShare]:
        """Generate share snapshots for all members in a group"""
        members = Member.query.filter_by(group_id=group_id, is_active=True).all()
        pool_principal = LedgerService.get_pool_balance(group_id)
        
        snapshots = []
        for member in members:
            member_principal = LedgerService.get_member_principal(member.user_id, group_id)
            
            if pool_principal > 0:
                share = member_principal / pool_principal
            else:
                share = Decimal('0')
            
            existing = MemberShare.query.filter_by(
                snapshot_date=snapshot_date,
                member_id=member.user_id,
                group_id=group_id
            ).first()
            
            if not existing:
                snapshot = MemberShare(
                    id=generate_id('share_'),
                    snapshot_date=snapshot_date,
                    member_id=member.user_id,
                    group_id=group_id,
                    pool_principal=pool_principal,
                    member_principal=member_principal,
                    member_share=share
                )
                db.session.add(snapshot)
                snapshots.append(snapshot)
        
        db.session.commit()
        return snapshots
    
    @staticmethod
    def update_tax_bucket_contribution(member_id: int, group_id: int, amount: Decimal):
        """Update tax bucket with contribution"""
        tax_year = datetime.utcnow().year
        bucket = TaxBucket.query.filter_by(
            member_id=member_id,
            group_id=group_id,
            tax_year=tax_year
        ).first()
        
        if not bucket:
            bucket = TaxBucket(
                id=generate_id('tax_'),
                member_id=member_id,
                group_id=group_id,
                tax_year=tax_year,
                taxable_interest=Decimal('0'),
                total_contributions=Decimal('0'),
                total_withdrawals=Decimal('0')
            )
            db.session.add(bucket)
        
        bucket.total_contributions = Decimal(str(bucket.total_contributions or 0)) + amount
        bucket.last_update = datetime.utcnow()
    
    @staticmethod
    def update_tax_bucket_withdrawal(member_id: int, group_id: int, amount: Decimal):
        """Update tax bucket with withdrawal"""
        tax_year = datetime.utcnow().year
        bucket = TaxBucket.query.filter_by(
            member_id=member_id,
            group_id=group_id,
            tax_year=tax_year
        ).first()
        
        if bucket:
            bucket.total_withdrawals = Decimal(str(bucket.total_withdrawals or 0)) + amount
            bucket.last_update = datetime.utcnow()
    
    @staticmethod
    def update_tax_bucket_interest(member_id: int, group_id: int, amount: Decimal, tax_year: int):
        """Update tax bucket with interest earnings"""
        bucket = TaxBucket.query.filter_by(
            member_id=member_id,
            group_id=group_id,
            tax_year=tax_year
        ).first()
        
        if not bucket:
            bucket = TaxBucket(
                id=generate_id('tax_'),
                member_id=member_id,
                group_id=group_id,
                tax_year=tax_year,
                taxable_interest=Decimal('0'),
                total_contributions=Decimal('0'),
                total_withdrawals=Decimal('0')
            )
            db.session.add(bucket)
        
        bucket.taxable_interest = Decimal(str(bucket.taxable_interest or 0)) + amount
        bucket.last_update = datetime.utcnow()

class ReconciliationService:
    """Ledger reconciliation and audit tools"""
    
    @staticmethod
    def verify_event_balance(event_id: str) -> Tuple[bool, Decimal]:
        """Verify a single event balances to zero"""
        total = db.session.query(
            db.func.sum(LedgerPosting.amount)
        ).filter(
            LedgerPosting.event_id == event_id
        ).scalar() or Decimal('0')
        
        return total == Decimal('0'), Decimal(str(total))
    
    @staticmethod
    def verify_all_events_balance() -> List[Tuple[str, Decimal]]:
        """Find any events that don't balance"""
        result = db.session.query(
            LedgerPosting.event_id,
            db.func.sum(LedgerPosting.amount)
        ).group_by(
            LedgerPosting.event_id
        ).having(
            db.func.sum(LedgerPosting.amount) != 0
        ).all()
        
        return [(row[0], Decimal(str(row[1]))) for row in result]
    
    @staticmethod
    def verify_pool_equals_members(group_id: int) -> Tuple[bool, Dict]:
        """Verify pool cash equals sum of member sub-accounts"""
        pool_cash = LedgerService.get_pool_balance(group_id)
        
        member_totals = db.session.query(
            db.func.coalesce(db.func.sum(LedgerPosting.amount), 0)
        ).filter(
            LedgerPosting.account_id.in_(['member_principal', 'member_earnings']),
            LedgerPosting.group_id == group_id
        ).scalar()
        
        member_totals = abs(Decimal(str(member_totals or 0)))
        
        rounding = db.session.query(
            db.func.coalesce(db.func.sum(LedgerPosting.amount), 0)
        ).filter(
            LedgerPosting.account_id == 'rounding_reserve',
            LedgerPosting.group_id == group_id
        ).scalar()
        
        rounding = Decimal(str(rounding or 0))
        
        diff = pool_cash - member_totals - rounding
        
        return diff == Decimal('0'), {
            'pool_cash': float(pool_cash),
            'member_totals': float(member_totals),
            'rounding_reserve': float(rounding),
            'difference': float(diff)
        }
    
    @staticmethod
    def run_full_reconciliation(group_id: int = None) -> Dict:
        """Run complete reconciliation check"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'events_checked': 0,
            'unbalanced_events': [],
            'groups_checked': [],
            'invariant_violations': []
        }
        
        unbalanced = ReconciliationService.verify_all_events_balance()
        results['unbalanced_events'] = [(e, float(d)) for e, d in unbalanced]
        results['events_checked'] = LedgerEvent.query.count()
        
        if group_id:
            groups = [Group.query.get(group_id)]
        else:
            groups = Group.query.all()
        
        for group in groups:
            if group:
                balanced, details = ReconciliationService.verify_pool_equals_members(group.id)
                group_result = {
                    'group_id': group.id,
                    'group_name': group.name,
                    'balanced': balanced,
                    'details': details
                }
                results['groups_checked'].append(group_result)
                
                if not balanced:
                    results['invariant_violations'].append(
                        f"Group {group.id} pool/member mismatch: {details['difference']}"
                    )
        
        results['passed'] = (
            len(results['unbalanced_events']) == 0 and
            len(results['invariant_violations']) == 0
        )
        
        return results

class TaxReportService:
    """Tax reporting and 1099-INT generation"""
    
    @staticmethod
    def generate_statement(member_id: int, group_id: int, tax_year: int) -> TaxReport:
        """Generate year-to-date statement"""
        position = LedgerService.get_member_position(member_id, group_id)
        
        bucket = TaxBucket.query.filter_by(
            member_id=member_id,
            group_id=group_id,
            tax_year=tax_year
        ).first()
        
        transactions = LedgerEvent.query.filter(
            LedgerEvent.group_id == group_id,
            LedgerEvent.meta['member_id'].astext == str(member_id),
            db.extract('year', LedgerEvent.ts) == tax_year
        ).order_by(LedgerEvent.ts).all()
        
        payload = {
            'member_id': member_id,
            'group_id': group_id,
            'tax_year': tax_year,
            'generated_at': datetime.utcnow().isoformat(),
            'position': position,
            'tax_bucket': {
                'taxable_interest': float(bucket.taxable_interest) if bucket else 0,
                'total_contributions': float(bucket.total_contributions) if bucket else 0,
                'total_withdrawals': float(bucket.total_withdrawals) if bucket else 0,
            },
            'transaction_count': len(transactions),
        }
        
        checksum = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        
        report = TaxReport(
            id=generate_id('rpt_'),
            member_id=member_id,
            group_id=group_id,
            tax_year=tax_year,
            report_type='statement',
            status='draft',
            payload=payload,
            checksum=checksum
        )
        
        db.session.add(report)
        db.session.commit()
        
        return report
    
    @staticmethod
    def generate_1099_int(
        member_id: int,
        tax_year: int,
        payer_info: Dict
    ) -> TaxReport:
        """Generate 1099-INT data"""
        user = User.query.get(member_id)
        
        total_interest = db.session.query(
            db.func.sum(TaxBucket.taxable_interest)
        ).filter(
            TaxBucket.member_id == member_id,
            TaxBucket.tax_year == tax_year
        ).scalar() or Decimal('0')
        
        payload = {
            'form_type': '1099-INT',
            'tax_year': tax_year,
            'payer': payer_info,
            'recipient': {
                'name': user.username,
                'email': user.email,
            },
            'box_1_interest': float(bankers_round(Decimal(str(total_interest)))),
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        checksum = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        
        report = TaxReport(
            id=generate_id('1099_'),
            member_id=member_id,
            group_id=None,
            tax_year=tax_year,
            report_type='1099-INT',
            status='draft',
            payload=payload,
            checksum=checksum
        )
        
        db.session.add(report)
        db.session.commit()
        
        return report
    
    @staticmethod
    def finalize_report(report_id: str) -> TaxReport:
        """Finalize a report (no further edits allowed)"""
        report = TaxReport.query.get(report_id)
        if not report:
            raise LedgerError(f"Report not found: {report_id}")
        
        if report.status == 'final':
            raise LedgerError("Report already finalized")
        
        report.status = 'final'
        report.finalized_at = datetime.utcnow()
        
        db.session.commit()
        return report
