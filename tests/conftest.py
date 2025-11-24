import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import app as flask_app, db
from models import User, Group, Member, Badge, FinancialTip

@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def test_admin_user(app):
    with app.app_context():
        admin = User(username='adminuser', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        return admin

@pytest.fixture
def test_group(app, test_admin_user):
    with app.app_context():
        group = Group(
            name='Test Group',
            description='A test savings group',
            contribution_amount=50.00,
            contribution_frequency='weekly',
            group_code='TEST123',
            require_admin_approval=True,
            created_by=test_admin_user.id
        )
        db.session.add(group)
        db.session.commit()
        
        admin_member = Member(
            user_id=test_admin_user.id,
            group_id=group.id,
            role='admin',
            approval_status='approved',
            is_active=True
        )
        db.session.add(admin_member)
        db.session.commit()
        
        return group
