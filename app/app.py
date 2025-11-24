from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, Response
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from models import db, User, Group, Member, Transaction, Badge, UserBadge
from werkzeug.utils import secure_filename
from utils import convert_currency, get_random_quote, check_and_award_badges, generate_group_report_csv, get_financial_advice, seed_initial_data, cleanup_old_receipts
from notifications import send_contribution_notification, send_approval_notification, send_badge_notification, send_payout_notification
import os
import secrets
from datetime import datetime

UPLOAD_FOLDER = 'app/uploads/receipts'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///tikob.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

csrf = CSRFProtect(app)
migrate = Migrate(app, db)
db.init_app(app)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

if os.environ.get('FLASK_ENV') == 'production':
    Talisman(app, force_https=True, strict_transport_security=True, 
             content_security_policy=None)

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

with app.app_context():
    db.create_all()
    seed_initial_data()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
@limiter.limit("5 per hour")
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
@limiter.limit("10 per hour")
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
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func, case
    
    user = User.query.get(session['user_id'])
    memberships = Member.query.options(joinedload(Member.group)).filter_by(
        user_id=user.id, 
        is_active=True
    ).all()
    
    group_ids = [m.group_id for m in memberships]
    
    group_stats = db.session.query(
        Transaction.group_id,
        func.sum(case((Transaction.transaction_type == 'contribution', Transaction.amount), else_=0)).label('total_contributions'),
        func.sum(case((Transaction.transaction_type == 'payout', Transaction.amount), else_=0)).label('total_payouts')
    ).filter(
        Transaction.group_id.in_(group_ids)
    ).group_by(Transaction.group_id).all()
    
    stats_dict = {stat.group_id: {'contributions': float(stat.total_contributions or 0), 'payouts': float(stat.total_payouts or 0)} for stat in group_stats}
    
    member_counts = db.session.query(
        Member.group_id,
        func.count(Member.id).label('count')
    ).filter(
        Member.group_id.in_(group_ids),
        Member.is_active == True
    ).group_by(Member.group_id).all()
    
    counts_dict = {mc.group_id: mc.count for mc in member_counts}
    
    groups_data = []
    for membership in memberships:
        group = membership.group
        stats = stats_dict.get(group.id, {'contributions': 0, 'payouts': 0})
        balance = stats['contributions'] - stats['payouts']
        
        groups_data.append({
            'group': group,
            'membership': membership,
            'balance': balance,
            'members_count': counts_dict.get(group.id, 0)
        })
    
    quote = get_random_quote()
    advice = get_financial_advice(user.id)
    recent_badges = UserBadge.query.options(joinedload(UserBadge.badge)).filter_by(
        user_id=user.id
    ).order_by(UserBadge.earned_at.desc()).limit(3).all()
    
    return render_template('dashboard.html', 
                          groups_data=groups_data, 
                          quote=quote,
                          advice=advice,
                          recent_badges=recent_badges)

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
            if group.require_admin_approval:
                existing_member.approval_status = 'pending'
                existing_member.is_active = False
                flash('Your request to rejoin is pending admin approval.', 'info')
            else:
                existing_member.is_active = True
                existing_member.approval_status = 'approved'
                flash('Rejoined group successfully!', 'success')
            db.session.commit()
        else:
            if group.require_admin_approval:
                member = Member(user_id=session['user_id'], group_id=group.id, role='member', 
                              approval_status='pending', is_active=False)
                flash('Your request to join is pending admin approval.', 'info')
            else:
                member = Member(user_id=session['user_id'], group_id=group.id, role='member', 
                              approval_status='approved', is_active=True)
                flash('Joined group successfully!', 'success')
            db.session.add(member)
            db.session.commit()
        
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
    
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func, case
    
    members = Member.query.options(joinedload(Member.user)).filter_by(
        group_id=group_id, 
        is_active=True
    ).all()
    
    member_ids = [m.id for m in members]
    
    transaction_stats = db.session.query(
        Transaction.member_id,
        func.sum(case((Transaction.transaction_type == 'contribution', Transaction.amount), else_=0)).label('total_contributed'),
        func.sum(case((Transaction.transaction_type == 'payout', Transaction.amount), else_=0)).label('total_received')
    ).filter(
        Transaction.member_id.in_(member_ids)
    ).group_by(Transaction.member_id).all()
    
    stats_dict = {
        stat.member_id: {
            'contributed': float(stat.total_contributed or 0),
            'received': float(stat.total_received or 0)
        } for stat in transaction_stats
    }
    
    member_stats = []
    for member in members:
        stats = stats_dict.get(member.id, {'contributed': 0, 'received': 0})
        member_stats.append({
            'member': member,
            'total_contributed': stats['contributed'],
            'total_received': stats['received']
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
    
    receipt_filename = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            receipt_filename = f"{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], receipt_filename))
    
    transaction = Transaction(
        group_id=group_id,
        member_id=member_id,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        receipt_filename=receipt_filename,
        verified=True if receipt_filename else False
    )
    db.session.add(transaction)
    db.session.commit()
    
    member = Member.query.get(member_id)
    
    active_members = Member.query.filter_by(group_id=group_id, is_active=True).all()
    for active_member in active_members:
        if transaction_type == 'contribution':
            send_contribution_notification(
                active_member.user.email,
                group.name,
                amount,
                member.user.username
            )
        else:
            send_payout_notification(
                active_member.user.email,
                group.name,
                amount,
                member.user.username
            )
    
    awarded_badges = check_and_award_badges(member.user_id)
    if awarded_badges:
        badge_names = ', '.join([b.name for b in awarded_badges])
        for badge in awarded_badges:
            send_badge_notification(member.user.email, badge.name, badge.description)
        flash(f'Transaction recorded! 🎉 New badges earned: {badge_names}', 'success')
    else:
        flash('Transaction recorded successfully!', 'success')
    
    return redirect(url_for('ledger', group_id=group_id))

@app.route('/group/<int:group_id>/ledger')
@login_required
def ledger(group_id):
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func, case
    
    group = Group.query.get_or_404(group_id)
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, is_active=True).first()
    
    if not membership:
        flash('You are not a member of this group.', 'danger')
        return redirect(url_for('dashboard'))
    
    transactions = Transaction.query.options(
        joinedload(Transaction.member).joinedload(Member.user)
    ).filter_by(group_id=group_id).order_by(Transaction.transaction_date.desc()).all()
    
    members = Member.query.options(joinedload(Member.user)).filter_by(
        group_id=group_id, 
        is_active=True
    ).all()
    
    totals = db.session.query(
        func.sum(case((Transaction.transaction_type == 'contribution', Transaction.amount), else_=0)).label('contributions'),
        func.sum(case((Transaction.transaction_type == 'payout', Transaction.amount), else_=0)).label('payouts')
    ).filter(Transaction.group_id == group_id).first()
    
    total_contributions = float(totals.contributions or 0)
    total_payouts = float(totals.payouts or 0)
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

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    admin_groups = Member.query.filter_by(user_id=session['user_id'], role='admin', is_active=True).all()
    
    pending_approvals = []
    for admin_membership in admin_groups:
        group = admin_membership.group
        pending_members = Member.query.filter_by(
            group_id=group.id,
            approval_status='pending'
        ).all()
        
        for pending in pending_members:
            pending_approvals.append({
                'member': pending,
                'group': group,
                'user': pending.user
            })
    
    quote = get_random_quote()
    return render_template('admin_dashboard.html', 
                          pending_approvals=pending_approvals,
                          admin_groups=admin_groups,
                          quote=quote)

@app.route('/group/<int:group_id>/approve-member/<int:member_id>', methods=['POST'])
@login_required
def approve_member(group_id, member_id):
    admin_membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, role='admin').first()
    
    if not admin_membership:
        flash('Only admins can approve members.', 'danger')
        return redirect(url_for('dashboard'))
    
    member = Member.query.get_or_404(member_id)
    member.approval_status = 'approved'
    member.is_active = True
    db.session.commit()
    
    send_approval_notification(member.user.email, admin_membership.group.name, approved=True)
    
    flash(f'{member.user.username} has been approved!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/group/<int:group_id>/reject-member/<int:member_id>', methods=['POST'])
@login_required
def reject_member(group_id, member_id):
    admin_membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id, role='admin').first()
    
    if not admin_membership:
        flash('Only admins can reject members.', 'danger')
        return redirect(url_for('dashboard'))
    
    member = Member.query.get_or_404(member_id)
    username = member.user.username
    user_email = member.user.email
    group_name = admin_membership.group.name
    db.session.delete(member)
    db.session.commit()
    
    send_approval_notification(user_email, group_name, approved=False)
    
    flash(f'{username}\'s request has been rejected.', 'info')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/group/<int:group_id>/export-report')
@login_required
def export_report(group_id):
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id).first()
    
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    csv_data = generate_group_report_csv(group_id)
    group = Group.query.get_or_404(group_id)
    filename = f"{group.name.replace(' ', '_')}_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )

@app.route('/my-badges')
@login_required
def my_badges():
    user = User.query.get(session['user_id'])
    user_badges = UserBadge.query.filter_by(user_id=user.id).all()
    all_badges = Badge.query.all()
    
    earned_badge_ids = [ub.badge_id for ub in user_badges]
    
    advice = get_financial_advice(user.id)
    quote = get_random_quote()
    
    return render_template('badges.html', 
                          user_badges=user_badges,
                          all_badges=all_badges,
                          earned_badge_ids=earned_badge_ids,
                          advice=advice,
                          quote=quote)

@app.route('/uploads/receipts/<filename>')
@login_required
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin/cleanup-receipts', methods=['POST'])
@login_required
def cleanup_receipts():
    admin_groups = Member.query.filter_by(user_id=session['user_id'], role='admin', is_active=True).first()
    
    if not admin_groups:
        flash('Only admins can perform cleanup operations.', 'danger')
        return redirect(url_for('dashboard'))
    
    result = cleanup_old_receipts(app.config['UPLOAD_FOLDER'], retention_days=90)
    
    if result['deleted'] > 0:
        flash(f'Cleanup completed: {result["deleted"]} old receipts removed.', 'success')
    else:
        flash('No old receipts to clean up.', 'info')
    
    if result['errors']:
        for error in result['errors']:
            flash(f'Error: {error}', 'warning')
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
