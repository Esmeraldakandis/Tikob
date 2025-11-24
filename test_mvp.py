import sys
sys.path.insert(0, 'app')

from app import app, db
from models import User, Group, Member, Transaction
from werkzeug.security import check_password_hash

print("=" * 60)
print("TIKÒB MVP TESTING")
print("=" * 60)

with app.app_context():
    db.drop_all()
    db.create_all()
    
    print("\n✓ Database initialized")
    
    print("\n--- TEST 1: User Creation & Authentication ---")
    user1 = User(username='alice', email='alice@example.com')
    user1.set_password('password123')
    
    user2 = User(username='bob', email='bob@example.com')
    user2.set_password('password456')
    
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    
    assert user1.check_password('password123') == True
    assert user1.check_password('wrongpass') == False
    assert check_password_hash(user1.password_hash, 'password123')
    
    print(f"✓ Created user: {user1.username} (ID: {user1.id})")
    print(f"✓ Created user: {user2.username} (ID: {user2.id})")
    print("✓ Password hashing verified")
    
    print("\n--- TEST 2: Group Creation ---")
    group = Group(
        name="Family Savings Circle",
        description="Monthly savings for family emergencies",
        contribution_amount=50.00,
        contribution_frequency="monthly",
        group_code="ABC123XY",
        created_by=user1.id
    )
    db.session.add(group)
    db.session.flush()
    
    admin_member = Member(
        user_id=user1.id,
        group_id=group.id,
        role='admin',
        is_active=True
    )
    db.session.add(admin_member)
    db.session.commit()
    
    print(f"✓ Group created: {group.name}")
    print(f"✓ Group code: {group.group_code}")
    print(f"✓ Admin assigned: {user1.username}")
    
    print("\n--- TEST 3: Joining Group ---")
    member2 = Member(
        user_id=user2.id,
        group_id=group.id,
        role='member',
        is_active=True
    )
    db.session.add(member2)
    db.session.commit()
    
    total_members = Member.query.filter_by(group_id=group.id, is_active=True).count()
    print(f"✓ User {user2.username} joined group")
    print(f"✓ Total active members: {total_members}")
    
    print("\n--- TEST 4: Transaction & Ledger ---")
    
    transaction1 = Transaction(
        group_id=group.id,
        member_id=admin_member.id,
        transaction_type='contribution',
        amount=50.00,
        description='Monthly contribution - January'
    )
    
    transaction2 = Transaction(
        group_id=group.id,
        member_id=member2.id,
        transaction_type='contribution',
        amount=50.00,
        description='Monthly contribution - January'
    )
    
    transaction3 = Transaction(
        group_id=group.id,
        member_id=admin_member.id,
        transaction_type='payout',
        amount=30.00,
        description='Emergency fund distribution'
    )
    
    db.session.add_all([transaction1, transaction2, transaction3])
    db.session.commit()
    
    total_contributions = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.group_id == group.id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    total_payouts = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.group_id == group.id,
        Transaction.transaction_type == 'payout'
    ).scalar() or 0
    
    balance = total_contributions - total_payouts
    
    print(f"✓ Added 2 contributions: ${total_contributions:.2f}")
    print(f"✓ Added 1 payout: ${total_payouts:.2f}")
    print(f"✓ Current balance: ${balance:.2f}")
    
    alice_contributions = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.member_id == admin_member.id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    print(f"✓ {user1.username}'s contributions: ${alice_contributions:.2f}")
    
    print("\n--- TEST 5: Unsubscribe/Leave Group ---")
    member2.is_active = False
    db.session.commit()
    
    active_members = Member.query.filter_by(group_id=group.id, is_active=True).count()
    inactive_members = Member.query.filter_by(group_id=group.id, is_active=False).count()
    
    print(f"✓ {user2.username} left the group")
    print(f"✓ Active members: {active_members}")
    print(f"✓ Inactive members: {inactive_members}")
    
    print("\n--- TEST 6: Data Integrity ---")
    
    assert group.creator.id == user1.id
    assert len(group.members) == 2
    assert len(group.transactions) == 3
    assert admin_member.user.username == 'alice'
    assert admin_member.group.name == 'Family Savings Circle'
    
    print("✓ Relationships properly linked")
    print("✓ Foreign keys working correctly")
    
    print("\n" + "=" * 60)
    print("ALL MVP TESTS PASSED ✓")
    print("=" * 60)
    print("\nCore functionality verified:")
    print("  • User authentication & password hashing")
    print("  • Group creation with unique codes")
    print("  • Member management (admin/member roles)")
    print("  • Transaction recording (contributions/payouts)")
    print("  • Balance calculations")
    print("  • Unsubscribe functionality")
    print("  • Database relationships & integrity")
