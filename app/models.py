from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    preferred_currency = db.Column(db.String(3), default='USD')
    notification_enabled = db.Column(db.Boolean, default=True)
    is_ghost = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    memberships = db.relationship('Member', back_populates='user', cascade='all, delete-orphan')
    badges = db.relationship('UserBadge', back_populates='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if self.is_ghost:
            return False
        return check_password_hash(self.password_hash, password)

class Tradition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    region = db.Column(db.String(100))
    cultural_theme = db.Column(db.String(50))
    icon = db.Column(db.String(10))
    is_custom = db.Column(db.Boolean, default=False)
    
    groups = db.relationship('Group', back_populates='tradition')

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    contribution_amount = db.Column(db.Float, nullable=False)
    contribution_frequency = db.Column(db.String(20), nullable=False)
    group_code = db.Column(db.String(10), unique=True, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    require_admin_approval = db.Column(db.Boolean, default=False)
    tradition_id = db.Column(db.Integer, db.ForeignKey('tradition.id'))
    cultural_theme = db.Column(db.String(50), default='default')
    
    members = db.relationship('Member', back_populates='group', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', back_populates='group', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by])
    tradition = db.relationship('Tradition', back_populates='groups')

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    role = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    approval_status = db.Column(db.String(20), default='approved')
    is_ghost = db.Column(db.Boolean, default=False)
    is_storyteller = db.Column(db.Boolean, default=False)
    reliability_score = db.Column(db.Integer, default=100)
    
    user = db.relationship('User', back_populates='memberships')
    group = db.relationship('Group', back_populates='members')
    transactions = db.relationship('Transaction', back_populates='member', cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'group_id', name='unique_user_group'),)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    receipt_filename = db.Column(db.String(255))
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean, default=False)
    
    group = db.relationship('Group', back_populates='transactions')
    member = db.relationship('Member', back_populates='transactions')

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    criteria_type = db.Column(db.String(50))
    criteria_value = db.Column(db.Integer)
    
    user_badges = db.relationship('UserBadge', back_populates='badge', cascade='all, delete-orphan')

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='badges')
    badge = db.relationship('Badge', back_populates='user_badges')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'badge_id', name='unique_user_badge'),)

class FinancialTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    is_motivational = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserXP(db.Model):
    __tablename__ = 'user_xp'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_xp = db.Column(db.Integer, default=0)
    current_level = db.Column(db.Integer, default=1)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_contribution_date = db.Column(db.DateTime)
    
    user = db.relationship('User', backref=db.backref('xp_profile', uselist=False))

class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rate'
    id = db.Column(db.Integer, primary_key=True)
    base_currency = db.Column(db.String(3), default='USD')
    target_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class UserCurrency(db.Model):
    __tablename__ = 'user_currency'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    preferred_currency = db.Column(db.String(3), default='USD')
    
    user = db.relationship('User', backref=db.backref('currency_pref', uselist=False))

class Challenge(db.Model):
    __tablename__ = 'challenge'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    challenge_type = db.Column(db.String(50))
    target_value = db.Column(db.Integer)
    xp_reward = db.Column(db.Integer, default=100)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    badge = db.relationship('Badge', backref='challenges')

class UserChallenge(db.Model):
    __tablename__ = 'user_challenge'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='challenges')
    challenge = db.relationship('Challenge', backref='user_challenges')

class FinancialGoal(db.Model):
    __tablename__ = 'financial_goal'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal_name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0)
    target_date = db.Column(db.DateTime)
    goal_type = db.Column(db.String(50))
    achieved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='financial_goals')

class PersonalizedAdvice(db.Model):
    __tablename__ = 'personalized_advice'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    advice_text = db.Column(db.Text, nullable=False)
    advice_type = db.Column(db.String(50))
    context_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    displayed = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='personalized_advice')

class UserFinancialProfile(db.Model):
    __tablename__ = 'user_financial_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    income_range = db.Column(db.String(50))
    savings_habit = db.Column(db.String(50))
    financial_goal = db.Column(db.String(100))
    risk_tolerance = db.Column(db.String(20))
    employment_status = db.Column(db.String(50))
    dependents = db.Column(db.Integer, default=0)
    has_emergency_fund = db.Column(db.Boolean, default=False)
    preferred_group_size = db.Column(db.String(20))
    contribution_comfort_level = db.Column(db.String(50))
    survey_completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('financial_profile', uselist=False))

class PlaidAccount(db.Model):
    __tablename__ = 'plaid_account'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.String(255), nullable=False)
    item_id = db.Column(db.String(255), nullable=False)
    institution_name = db.Column(db.String(100))
    account_id = db.Column(db.String(255))
    account_name = db.Column(db.String(100))
    account_type = db.Column(db.String(50))
    account_subtype = db.Column(db.String(50))
    current_balance = db.Column(db.Float, default=0)
    available_balance = db.Column(db.Float, default=0)
    currency_code = db.Column(db.String(10), default='USD')
    is_active = db.Column(db.Boolean, default=True)
    last_synced = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='plaid_accounts')

class PersonalTransaction(db.Model):
    __tablename__ = 'personal_transaction'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plaid_account_id = db.Column(db.Integer, db.ForeignKey('plaid_account.id'))
    transaction_id = db.Column(db.String(255))
    transaction_type = db.Column(db.String(20))
    category = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    merchant_name = db.Column(db.String(100))
    transaction_date = db.Column(db.DateTime, nullable=False)
    is_income = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='personal_transactions')
    plaid_account = db.relationship('PlaidAccount', backref='transactions')

class TellerAccount(db.Model):
    __tablename__ = 'teller_account'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.String(255), nullable=False)
    enrollment_id = db.Column(db.String(255), nullable=False)
    account_id = db.Column(db.String(255))
    account_name = db.Column(db.String(100))
    account_type = db.Column(db.String(50))
    account_subtype = db.Column(db.String(50))
    institution_name = db.Column(db.String(100))
    institution_id = db.Column(db.String(100))
    last_four = db.Column(db.String(4))
    is_active = db.Column(db.Boolean, default=True)
    last_synced = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='teller_accounts')

class GroupMessage(db.Model):
    __tablename__ = 'group_message'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')
    audio_url = db.Column(db.String(500))
    audio_duration = db.Column(db.Float)
    is_proverb = db.Column(db.Boolean, default=False)
    proverb_context = db.Column(db.Text)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('group_message.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    
    group = db.relationship('Group', backref='messages')
    user = db.relationship('User', backref='messages')
    parent = db.relationship('GroupMessage', remote_side=[id], backref='replies')
    reactions = db.relationship('MessageReaction', back_populates='message', cascade='all, delete-orphan')

class MessageReaction(db.Model):
    __tablename__ = 'message_reaction'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('group_message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    emoji = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    message = db.relationship('GroupMessage', back_populates='reactions')
    user = db.relationship('User', backref='reactions')
    
    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', 'emoji', name='unique_message_reaction'),)
