import csv
import io
from datetime import datetime
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

def check_and_award_badges(user_id):
    user_badges = UserBadge.query.filter_by(user_id=user_id).all()
    awarded_badge_ids = [ub.badge_id for ub in user_badges]
    
    total_contributions = db.session.query(db.func.sum(Transaction.amount)).join(
        Member
    ).filter(
        Member.user_id == user_id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    memberships_count = Member.query.filter_by(user_id=user_id, is_active=True).count()
    
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
