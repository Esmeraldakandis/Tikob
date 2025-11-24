import pytest
from models import Badge, UserBadge, Transaction, Member, db
from utils import check_and_award_badges

def test_badge_awarding_first_contribution(app, test_user, test_group, test_admin_user):
    with app.app_context():
        badge = Badge(
            name='First Contribution',
            description='Made your first contribution',
            icon='🌟',
            criteria_type='total_contributions',
            criteria_value=1
        )
        db.session.add(badge)
        
        member = Member(
            user_id=test_user.id,
            group_id=test_group.id,
            role='member',
            approval_status='approved',
            is_active=True
        )
        db.session.add(member)
        db.session.commit()
        
        transaction = Transaction(
            group_id=test_group.id,
            member_id=member.id,
            transaction_type='contribution',
            amount=50.00,
            description='First contribution'
        )
        db.session.add(transaction)
        db.session.commit()
        
        awarded = check_and_award_badges(test_user.id)
        
        assert len(awarded) == 1
        assert awarded[0].name == 'First Contribution'
        
        user_badge = UserBadge.query.filter_by(
            user_id=test_user.id,
            badge_id=badge.id
        ).first()
        
        assert user_badge is not None

def test_badge_not_awarded_twice(app, test_user, test_group):
    with app.app_context():
        badge = Badge(
            name='Steady Saver',
            description='Contributed $100 or more',
            icon='💪',
            criteria_type='total_contributions',
            criteria_value=100
        )
        db.session.add(badge)
        
        member = Member(
            user_id=test_user.id,
            group_id=test_group.id,
            role='member',
            approval_status='approved',
            is_active=True
        )
        db.session.add(member)
        db.session.commit()
        
        transaction1 = Transaction(
            group_id=test_group.id,
            member_id=member.id,
            transaction_type='contribution',
            amount=100.00
        )
        db.session.add(transaction1)
        db.session.commit()
        
        awarded1 = check_and_award_badges(test_user.id)
        assert len(awarded1) == 1
        
        transaction2 = Transaction(
            group_id=test_group.id,
            member_id=member.id,
            transaction_type='contribution',
            amount=50.00
        )
        db.session.add(transaction2)
        db.session.commit()
        
        awarded2 = check_and_award_badges(test_user.id)
        assert len(awarded2) == 0
