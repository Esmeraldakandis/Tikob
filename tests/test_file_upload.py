import pytest
import io
from werkzeug.datastructures import FileStorage
from models import Member

def test_transaction_with_receipt_upload(client, app, test_group, test_admin_user):
    with app.app_context():
        admin_member = Member.query.filter_by(
            user_id=test_admin_user.id,
            group_id=test_group.id
        ).first()
    
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin_user.id
        sess['username'] = test_admin_user.username
    
    data = {
        'transaction_type': 'contribution',
        'amount': 50.00,
        'description': 'Test contribution',
        'member_id': admin_member.id,
        'receipt': (io.BytesIO(b'fake image content'), 'receipt.jpg')
    }
    
    response = client.post(
        f'/group/{test_group.id}/add-transaction',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    assert response.status_code == 200

def test_invalid_file_type_rejected(client, app, test_group, test_admin_user):
    with app.app_context():
        admin_member = Member.query.filter_by(
            user_id=test_admin_user.id,
            group_id=test_group.id
        ).first()
    
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin_user.id
        sess['username'] = test_admin_user.username
    
    data = {
        'transaction_type': 'contribution',
        'amount': 50.00,
        'description': 'Test contribution',
        'member_id': admin_member.id,
        'receipt': (io.BytesIO(b'fake file'), 'malicious.exe')
    }
    
    response = client.post(
        f'/group/{test_group.id}/add-transaction',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    assert response.status_code == 200

def test_transaction_without_receipt(client, app, test_group, test_admin_user):
    with app.app_context():
        admin_member = Member.query.filter_by(
            user_id=test_admin_user.id,
            group_id=test_group.id
        ).first()
    
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin_user.id
        sess['username'] = test_admin_user.username
    
    response = client.post(
        f'/group/{test_group.id}/add-transaction',
        data={
            'transaction_type': 'contribution',
            'amount': 50.00,
            'description': 'Test contribution',
            'member_id': admin_member.id
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    assert b'Transaction recorded' in response.data
