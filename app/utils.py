import csv
import io
import os
from datetime import datetime, timedelta
from models import db, Badge, UserBadge, FinancialTip, Transaction, Member
import random

CURRENCY_RATES = {
    'USD': 1.0,
    'EUR': 0.92,
    'GBP': 0.79,
    'HTG': 131.50,
    'CAD': 1.36,
    'XOF': 602.50,
}

MOTIVATIONAL_QUOTES = [
    "Small steps lead to big dreams. Every contribution counts!",
    "Together we rise, together we thrive.",
    "Financial freedom starts with a single decision to save.",
    "Your future self will thank you for saving today.",
    "Community strength is built one contribution at a time.",
    "Saving is not about sacrifice; it's about priorities.",
    "The best time to start saving was yesterday. The second best time is today.",
    "Unity in savings creates prosperity for all.",
]

def convert_currency(amount, from_currency, to_currency):
    if from_currency == to_currency:
        return amount
    
    usd_amount = amount / CURRENCY_RATES.get(from_currency, 1.0)
    converted = usd_amount * CURRENCY_RATES.get(to_currency, 1.0)
    return round(converted, 2)

def get_random_quote():
    return random.choice(MOTIVATIONAL_QUOTES)

def calculate_user_streak(user_id):
    """Calculate the current contribution streak for a user (in weeks)."""
    from models import UserXP
    
    user_xp = UserXP.query.filter_by(user_id=user_id).first()
    if user_xp:
        return user_xp.current_streak // 7
    return 0

def calculate_highest_single_contribution(user_id):
    """Get the highest single contribution amount for a user."""
    highest = db.session.query(db.func.max(Transaction.amount)).join(
        Member
    ).filter(
        Member.user_id == user_id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    return highest

def calculate_membership_duration_months(user_id):
    """Calculate how many months the user has been active in any group."""
    earliest_membership = Member.query.filter_by(
        user_id=user_id, is_active=True
    ).order_by(Member.joined_at.asc()).first()
    
    if earliest_membership:
        days_active = (datetime.utcnow() - earliest_membership.joined_at).days
        return days_active // 30
    return 0

def calculate_reputation_score_for_badges(user_id):
    """Calculate reputation score for badge awarding (simplified version)."""
    memberships = Member.query.filter_by(user_id=user_id, is_active=True).all()
    
    if not memberships:
        return 0
    
    contribution_counts = []
    for membership in memberships:
        count = Transaction.query.filter_by(
            member_id=membership.id,
            transaction_type='contribution'
        ).count()
        contribution_counts.append(count)
    
    avg_contributions = sum(contribution_counts) / len(contribution_counts) if contribution_counts else 0
    
    consistency_score = min(avg_contributions * 10, 60)
    activity_score = min(len(memberships) * 10, 40)
    
    return int(consistency_score + activity_score)

def check_and_award_badges(user_id):
    """Check and award all types of badges to a user."""
    user_badges = UserBadge.query.filter_by(user_id=user_id).all()
    awarded_badge_ids = [ub.badge_id for ub in user_badges]
    
    total_contributions = db.session.query(db.func.sum(Transaction.amount)).join(
        Member
    ).filter(
        Member.user_id == user_id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    memberships_count = Member.query.filter_by(user_id=user_id, is_active=True).count()
    
    streak_weeks = calculate_user_streak(user_id)
    highest_contribution = calculate_highest_single_contribution(user_id)
    loyalty_months = calculate_membership_duration_months(user_id)
    reputation_score = calculate_reputation_score_for_badges(user_id)
    
    badges_to_award = []
    all_badges = Badge.query.all()
    
    for badge in all_badges:
        if badge.id in awarded_badge_ids:
            continue
            
        if badge.criteria_type == 'total_contributions':
            if total_contributions >= badge.criteria_value:
                badges_to_award.append(badge)
        elif badge.criteria_type == 'group_count':
            if memberships_count >= badge.criteria_value:
                badges_to_award.append(badge)
        elif badge.criteria_type == 'streak':
            if streak_weeks >= badge.criteria_value:
                badges_to_award.append(badge)
        elif badge.criteria_type == 'high_contribution':
            if highest_contribution >= badge.criteria_value:
                badges_to_award.append(badge)
        elif badge.criteria_type == 'loyalty':
            if loyalty_months >= badge.criteria_value:
                badges_to_award.append(badge)
        elif badge.criteria_type == 'reputation':
            if reputation_score >= badge.criteria_value:
                badges_to_award.append(badge)
    
    for badge in badges_to_award:
        user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
        db.session.add(user_badge)
    
    if badges_to_award:
        db.session.commit()
    
    return badges_to_award

def generate_group_report_csv(group_id):
    from models import Group, Member, Transaction
    
    group = Group.query.get_or_404(group_id)
    members = Member.query.filter_by(group_id=group_id, is_active=True).all()
    transactions = Transaction.query.filter_by(group_id=group_id).order_by(Transaction.transaction_date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['TiKòb Financial Report'])
    writer.writerow(['Group:', group.name])
    writer.writerow(['Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([])
    
    writer.writerow(['SUMMARY'])
    writer.writerow(['Total Members', len(members)])
    writer.writerow(['Contribution Amount', f'{group.currency} {group.contribution_amount}'])
    writer.writerow(['Frequency', group.contribution_frequency])
    writer.writerow([])
    
    total_contributions = sum(t.amount for t in transactions if t.transaction_type == 'contribution')
    total_payouts = sum(t.amount for t in transactions if t.transaction_type == 'payout')
    
    writer.writerow(['Total Contributions', f'{group.currency} {total_contributions:.2f}'])
    writer.writerow(['Total Payouts', f'{group.currency} {total_payouts:.2f}'])
    writer.writerow(['Current Balance', f'{group.currency} {(total_contributions - total_payouts):.2f}'])
    writer.writerow([])
    
    writer.writerow(['MEMBER DETAILS'])
    writer.writerow(['Username', 'Role', 'Joined', 'Total Contributed', 'Total Received'])
    
    for member in members:
        member_contributions = sum(t.amount for t in member.transactions if t.transaction_type == 'contribution')
        member_payouts = sum(t.amount for t in member.transactions if t.transaction_type == 'payout')
        
        writer.writerow([
            member.user.username,
            member.role,
            member.joined_at.strftime('%Y-%m-%d'),
            f'{group.currency} {member_contributions:.2f}',
            f'{group.currency} {member_payouts:.2f}'
        ])
    
    writer.writerow([])
    writer.writerow(['TRANSACTION HISTORY'])
    writer.writerow(['Date', 'Member', 'Type', 'Amount', 'Description', 'Verified'])
    
    for transaction in transactions:
        writer.writerow([
            transaction.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.member.user.username,
            transaction.transaction_type,
            f'{group.currency} {transaction.amount:.2f}',
            transaction.description or '',
            'Yes' if transaction.verified else 'No'
        ])
    
    output.seek(0)
    return output.getvalue()

def get_financial_advice(user_id):
    from models import Member, Transaction
    
    tips = FinancialTip.query.order_by(db.func.random()).limit(3).all()
    
    total_saved = db.session.query(db.func.sum(Transaction.amount)).join(
        Member
    ).filter(
        Member.user_id == user_id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    groups_count = Member.query.filter_by(user_id=user_id, is_active=True).count()
    
    advice = {
        'tips': tips,
        'total_saved': total_saved,
        'groups_count': groups_count,
        'next_goal': calculate_next_goal(total_saved)
    }
    
    return advice

def calculate_next_goal(current_total):
    goals = [100, 250, 500, 1000, 2500, 5000, 10000]
    
    for goal in goals:
        if current_total < goal:
            return {
                'amount': goal,
                'progress': (current_total / goal) * 100,
                'remaining': goal - current_total
            }
    
    return {
        'amount': current_total + 5000,
        'progress': 0,
        'remaining': 5000
    }

def seed_initial_data():
    if Badge.query.count() == 0:
        badges = [
            Badge(name='First Contribution', description='Made your first contribution', icon='🌟', criteria_type='total_contributions', criteria_value=1),
            Badge(name='Steady Saver', description='Contributed $100 or more', icon='💪', criteria_type='total_contributions', criteria_value=100),
            Badge(name='Super Saver', description='Contributed $500 or more', icon='🚀', criteria_type='total_contributions', criteria_value=500),
            Badge(name='Savings Champion', description='Contributed $1000 or more', icon='👑', criteria_type='total_contributions', criteria_value=1000),
            Badge(name='Community Builder', description='Joined 3 groups', icon='🤝', criteria_type='group_count', criteria_value=3),
            Badge(name='Group Leader', description='Joined 5 groups', icon='⭐', criteria_type='group_count', criteria_value=5),
            Badge(name='Consistency Bronze', description='4-week contribution streak', icon='🔥', criteria_type='streak', criteria_value=4),
            Badge(name='Consistency Silver', description='8-week contribution streak', icon='🔥', criteria_type='streak', criteria_value=8),
            Badge(name='Consistency Gold', description='12-week contribution streak', icon='🏆', criteria_type='streak', criteria_value=12),
            Badge(name='High Roller Bronze', description='Single contribution of $250+', icon='💎', criteria_type='high_contribution', criteria_value=250),
            Badge(name='High Roller Gold', description='Single contribution of $500+', icon='💎', criteria_type='high_contribution', criteria_value=500),
            Badge(name='High Roller Platinum', description='Single contribution of $1000+', icon='👑', criteria_type='high_contribution', criteria_value=1000),
            Badge(name='Loyalty Bronze', description='Active member for 3+ months', icon='❤️', criteria_type='loyalty', criteria_value=3),
            Badge(name='Loyalty Silver', description='Active member for 6+ months', icon='💜', criteria_type='loyalty', criteria_value=6),
            Badge(name='Loyalty Gold', description='Active member for 12+ months', icon='💛', criteria_type='loyalty', criteria_value=12),
            Badge(name='Elite Contributor', description='Reputation score of 80+', icon='🎖️', criteria_type='reputation', criteria_value=80),
            Badge(name='Legend Status', description='Reputation score of 95+', icon='🏅', criteria_type='reputation', criteria_value=95),
        ]
        db.session.add_all(badges)
    
    if FinancialTip.query.count() == 0:
        tips = [
            FinancialTip(title='Start Small', content='Even small contributions add up over time. Consistency is more important than the amount.', category='savings', is_motivational=False),
            FinancialTip(title='Emergency Fund', content='Aim to save 3-6 months of expenses for unexpected emergencies.', category='planning', is_motivational=False),
            FinancialTip(title='Track Your Progress', content='Regular review of your savings helps you stay motivated and on track.', category='habits', is_motivational=False),
            FinancialTip(title='Believe in Yourself', content='Your commitment to saving today is an investment in your tomorrow!', category='mindset', is_motivational=True),
            FinancialTip(title='Community Power', content='Saving together makes the journey easier and more rewarding.', category='community', is_motivational=True),
            FinancialTip(title='Set Clear Goals', content='Define what you are saving for - it makes staying motivated much easier.', category='planning', is_motivational=False),
        ]
        db.session.add_all(tips)
    
    db.session.commit()

def cleanup_old_receipts(upload_folder, retention_days=90):
    if not os.path.exists(upload_folder):
        return {'deleted': 0, 'errors': []}
    
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    deleted_count = 0
    errors = []
    
    active_receipts = set()
    recent_transactions = Transaction.query.filter(
        Transaction.receipt_filename.isnot(None),
        Transaction.transaction_date >= cutoff_date
    ).all()
    for t in recent_transactions:
        active_receipts.add(t.receipt_filename)
    
    try:
        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            
            if not os.path.isfile(filepath):
                continue
            
            file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            if file_modified_time < cutoff_date and filename not in active_receipts:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Failed to delete {filename}: {str(e)}")
    except Exception as e:
        errors.append(f"Error scanning directory: {str(e)}")
    
    return {
        'deleted': deleted_count,
        'errors': errors,
        'retention_days': retention_days
    }
