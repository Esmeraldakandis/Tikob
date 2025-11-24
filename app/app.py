from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Group, Member, Transaction
import os
import secrets
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tikob.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('signup'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    memberships = Member.query.filter_by(user_id=user.id, is_active=True).all()
    
    groups_data = []
    for membership in memberships:
        group = membership.group
        total_contributions = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.group_id == group.id,
            Transaction.transaction_type == 'contribution'
        ).scalar() or 0
        
        total_payouts = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.group_id == group.id,
            Transaction.transaction_type == 'payout'
        ).scalar() or 0
        
        balance = total_contributions - total_payouts
        
        groups_data.append({
            'group': group,
            'membership': membership,
            'balance': balance,
            'members_count': Member.query.filter_by(group_id=group.id, is_active=True).count()
        })
    
    return render_template('dashboard.html', groups_data=groups_data)

@app.route('/create-group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        contribution_amount = float(request.form.get('contribution_amount'))
        contribution_frequency = request.form.get('contribution_frequency')
        
        group_code = secrets.token_hex(4).upper()
        
        group = Group(
            name=name,
            description=description,
            contribution_amount=contribution_amount,
            contribution_frequency=contribution_frequency,
            group_code=group_code,
            created_by=session['user_id']
        )
        db.session.add(group)
        db.session.flush()
        
        member = Member(user_id=session['user_id'], group_id=group.id, role='admin')
        db.session.add(member)
        db.session.commit()
        
        flash(f'Group created successfully! Group code: {group_code}', 'success')
        return redirect(url_for('group_detail', group_id=group.id))
    
    return render_template('create_group.html')

@app.route('/join-group', methods=['GET', 'POST'])
@login_required
def join_group():
    if request.method == 'POST':
        group_code = request.form.get('group_code').upper()
        
        group = Group.query.filter_by(group_code=group_code).first()
        
        if not group:
            flash('Invalid group code.', 'danger')
            return redirect(url_for('join_group'))
        
        existing_member = Member.query.filter_by(
            user_id=session['user_id'],
            group_id=group.id
        ).first()
        
        if existing_member and existing_member.is_active:
            flash('You are already a member of this group.', 'warning')
            return redirect(url_for('group_detail', group_id=group.id))
        elif existing_member:
            existing_member.is_active = True
            db.session.commit()
            flash('Rejoined group successfully!', 'success')
        else:
            member = Member(user_id=session['user_id'], group_id=group.id, role='member')
            db.session.add(member)
            db.session.commit()
            flash('Joined group successfully!', 'success')
        
        return redirect(url_for('group_detail', group_id=group.id))
    
    return render_template('join_group.html')

@app.route('/group/<int:group_id>')
@login_required
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, is_active=True).first()
    
    if not membership:
        flash('You are not a member of this group.', 'danger')
        return redirect(url_for('dashboard'))
    
    members = Member.query.filter_by(group_id=group_id, is_active=True).all()
    
    member_stats = []
    for member in members:
        total_contributed = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.member_id == member.id,
            Transaction.transaction_type == 'contribution'
        ).scalar() or 0
        
        total_received = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.member_id == member.id,
            Transaction.transaction_type == 'payout'
        ).scalar() or 0
        
        member_stats.append({
            'member': member,
            'total_contributed': total_contributed,
            'total_received': total_received
        })
    
    return render_template('group_detail.html', group=group, membership=membership, member_stats=member_stats)

@app.route('/group/<int:group_id>/add-transaction', methods=['POST'])
@login_required
def add_transaction(group_id):
    group = Group.query.get_or_404(group_id)
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, is_active=True).first()
    
    if not membership:
        flash('You are not a member of this group.', 'danger')
        return redirect(url_for('dashboard'))
    
    transaction_type = request.form.get('transaction_type')
    amount = float(request.form.get('amount'))
    description = request.form.get('description')
    member_id = int(request.form.get('member_id'))
    
    transaction = Transaction(
        group_id=group_id,
        member_id=member_id,
        transaction_type=transaction_type,
        amount=amount,
        description=description
    )
    db.session.add(transaction)
    db.session.commit()
    
    flash('Transaction recorded successfully!', 'success')
    return redirect(url_for('ledger', group_id=group_id))

@app.route('/group/<int:group_id>/ledger')
@login_required
def ledger(group_id):
    group = Group.query.get_or_404(group_id)
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, is_active=True).first()
    
    if not membership:
        flash('You are not a member of this group.', 'danger')
        return redirect(url_for('dashboard'))
    
    transactions = Transaction.query.filter_by(group_id=group_id).order_by(Transaction.transaction_date.desc()).all()
    
    members = Member.query.filter_by(group_id=group_id, is_active=True).all()
    
    total_contributions = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.group_id == group_id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    total_payouts = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.group_id == group_id,
        Transaction.transaction_type == 'payout'
    ).scalar() or 0
    
    balance = total_contributions - total_payouts
    
    return render_template('ledger.html', 
                          group=group, 
                          membership=membership,
                          transactions=transactions, 
                          members=members,
                          total_contributions=total_contributions,
                          total_payouts=total_payouts,
                          balance=balance)

@app.route('/group/<int:group_id>/unsubscribe', methods=['POST'])
@login_required
def unsubscribe(group_id):
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, is_active=True).first()
    
    if membership:
        membership.is_active = False
        db.session.commit()
        flash('You have left the group.', 'success')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
