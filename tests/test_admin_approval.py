import pytest
from models import Member, db

def test_join_group_with_approval_required(client, app, test_group, test_user):
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['username'] = test_user.username
    
    response = client.post('/join-group', data={
        'group_code': 'TEST123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'pending admin approval' in response.data
    
    with app.app_context():
        membership = Member.query.filter_by(
            user_id=test_user.id,
            group_id=test_group.id
        ).first()
        
        assert membership is not None
        assert membership.approval_status == 'pending'
        assert membership.is_active == False

def test_admin_approve_member(client, app, test_group, test_user, test_admin_user):
    with app.app_context():
        pending_member = Member(
            user_id=test_user.id,
            group_id=test_group.id,
            role='member',
            approval_status='pending',
            is_active=False
        )
        db.session.add(pending_member)
        db.session.commit()
        member_id = pending_member.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin_user.id
        sess['username'] = test_admin_user.username
    
    response = client.post(
        f'/group/{test_group.id}/approve-member/{member_id}',
        follow_redirects=True
    )
    
    assert response.status_code == 200
    assert b'approved' in response.data
    
    with app.app_context():
        approved_member = Member.query.get(member_id)
        assert approved_member.approval_status == 'approved'
        assert approved_member.is_active == True

def test_admin_reject_member(client, app, test_group, test_user, test_admin_user):
    with app.app_context():
        pending_member = Member(
            user_id=test_user.id,
            group_id=test_group.id,
            role='member',
            approval_status='pending',
            is_active=False
        )
        db.session.add(pending_member)
        db.session.commit()
        member_id = pending_member.id
    
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin_user.id
        sess['username'] = test_admin_user.username
    
    response = client.post(
        f'/group/{test_group.id}/reject-member/{member_id}',
        follow_redirects=True
    )
    
    assert response.status_code == 200
    assert b'rejected' in response.data
    
    with app.app_context():
        rejected_member = Member.query.get(member_id)
        assert rejected_member is None

def test_admin_dashboard_shows_pending(client, app, test_group, test_user, test_admin_user):
    with app.app_context():
        pending_member = Member(
            user_id=test_user.id,
            group_id=test_group.id,
            role='member',
            approval_status='pending',
            is_active=False
        )
        db.session.add(pending_member)
        db.session.commit()
    
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin_user.id
        sess['username'] = test_admin_user.username
    
    response = client.get('/admin-dashboard')
    
    assert response.status_code == 200
    assert b'testuser' in response.data
    assert b'Pending Approvals' in response.data
