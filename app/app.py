from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, Response, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, User, Group, Member, Transaction, Badge, UserBadge, GroupMessage, MessageReaction, TellerAccount
from werkzeug.utils import secure_filename
from utils import convert_currency, get_random_quote, check_and_award_badges, generate_group_report_csv, get_financial_advice, seed_initial_data, cleanup_old_receipts
from notifications import send_contribution_notification, send_approval_notification, send_badge_notification, send_payout_notification
from xp_service import award_xp, update_streak, get_user_rank, check_challenge_progress
from advice_service import get_latest_advice
from currency_service import fetch_exchange_rates, convert_amount, get_user_currency, format_currency
from haitian_culture import get_random_proverb, get_financial_wisdom, get_community_phrase
from avatar_helper import get_user_initials, get_avatar_color
from ledger_service import LedgerService, ReconciliationService, TaxReportService, LedgerError
from ai_service import generate_haitian_proverb, get_language_options, get_all_ui_texts, UI_TRANSLATIONS, SUPPORTED_LANGUAGES
from decimal import Decimal
import os
import secrets
from datetime import datetime, date
from collections import defaultdict
import time

login_attempts = defaultdict(list)
LOGIN_BLOCK_DURATION = 900
MAX_LOGIN_ATTEMPTS = 5

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
socketio = SocketIO(app, cors_allowed_origins="*")

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
    from traditions_data import seed_traditions
    try:
        seed_traditions()
    except Exception as e:
        print(f"Note: Traditions already seeded or error: {e}")

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
@limiter.limit("10 per minute")
def signup():
    language = session.get('language', 'en')
    t = get_all_ui_texts(language)
    languages = get_language_options()
    
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
    
    return render_template('signup.html', t=t, languages=languages)

def is_login_blocked(ip_address):
    """Check if IP is blocked due to too many failed login attempts."""
    current_time = time.time()
    attempts = login_attempts[ip_address]
    attempts = [t for t in attempts if current_time - t < LOGIN_BLOCK_DURATION]
    login_attempts[ip_address] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS

def record_failed_login(ip_address):
    """Record a failed login attempt."""
    login_attempts[ip_address].append(time.time())

def clear_login_attempts(ip_address):
    """Clear login attempts after successful login."""
    login_attempts[ip_address] = []

def get_block_time_remaining(ip_address):
    """Get remaining block time in minutes."""
    if not login_attempts[ip_address]:
        return 0
    oldest_attempt = min(login_attempts[ip_address])
    elapsed = time.time() - oldest_attempt
    remaining = LOGIN_BLOCK_DURATION - elapsed
    return max(0, int(remaining / 60) + 1)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def login():
    ip_address = request.remote_addr
    language = session.get('language', 'en')
    t = get_all_ui_texts(language)
    languages = get_language_options()
    
    login_blocked = is_login_blocked(ip_address)
    block_minutes = get_block_time_remaining(ip_address) if login_blocked else 0
    
    if request.method == 'POST':
        if login_blocked:
            flash('Too many failed attempts. Please wait before trying again.', 'danger')
            return render_template('login.html', t=t, languages=languages, 
                                 login_blocked=True, block_minutes=block_minutes)
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            clear_login_attempts(ip_address)
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Logged in successfully!', 'success')
            
            from models import UserFinancialProfile
            has_profile = UserFinancialProfile.query.filter_by(user_id=user.id).first()
            if not has_profile:
                return redirect(url_for('financial_survey'))
            return redirect(url_for('dashboard'))
        else:
            record_failed_login(ip_address)
            remaining_attempts = MAX_LOGIN_ATTEMPTS - len(login_attempts[ip_address])
            if remaining_attempts > 0:
                flash(f'Invalid username or password. {remaining_attempts} attempts remaining.', 'danger')
            else:
                flash('Too many failed attempts. Please wait 15 minutes.', 'danger')
                return render_template('login.html', t=t, languages=languages, 
                                     login_blocked=True, block_minutes=15)
    
    return render_template('login.html', t=t, languages=languages, 
                         login_blocked=login_blocked, block_minutes=block_minutes)

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
    
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    advice = get_financial_advice(user.id)
    recent_badges = UserBadge.query.options(joinedload(UserBadge.badge)).filter_by(
        user_id=user.id
    ).order_by(UserBadge.earned_at.desc()).limit(3).all()
    
    from models import UserFinancialProfile
    has_survey = UserFinancialProfile.query.filter_by(user_id=user.id).first() is not None
    
    return render_template('dashboard.html', 
                          groups_data=groups_data, 
                          proverb=proverb,
                          advice=advice,
                          recent_badges=recent_badges,
                          language=language,
                          has_survey=has_survey)

@app.route('/impact')
@login_required
def impact_visualizer():
    from sqlalchemy import func
    
    user = db.session.get(User, session['user_id'])
    language = session.get('language', 'en')
    
    user_group_ids = [m.group_id for m in Member.query.filter_by(user_id=user.id, is_active=True).all()]
    
    my_contributions = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_type == 'contribution'
    ).scalar() or 0
    
    my_payouts = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_type == 'payout'
    ).scalar() or 0
    
    my_net_savings = float(my_contributions) - float(my_payouts)
    
    community_contributions = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(Transaction.transaction_type == 'contribution').scalar() or 0
    
    community_payouts = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(Transaction.transaction_type == 'payout').scalar() or 0
    
    community_net = float(community_contributions) - float(community_payouts)
    
    total_members = User.query.count()
    total_groups = Group.query.count()
    
    stats = {
        'my_savings': my_net_savings,
        'community_savings': community_net,
        'total_members': total_members,
        'total_groups': total_groups,
        'my_groups': len(user_group_ids),
        'countries': 8
    }
    
    if my_net_savings >= 10000:
        milestone_progress = 100
    elif my_net_savings >= 5000:
        milestone_progress = 80
    elif my_net_savings >= 1000:
        milestone_progress = 60
    elif my_net_savings >= 500:
        milestone_progress = 40
    elif my_net_savings >= 100:
        milestone_progress = 20
    else:
        milestone_progress = max(5, (my_net_savings / 100) * 20) if my_net_savings > 0 else 5
    
    recent_transactions = Transaction.query.filter(
        Transaction.group_id.in_(user_group_ids)
    ).order_by(
        Transaction.timestamp.desc()
    ).limit(10).all() if user_group_ids else []
    
    recent_activities = []
    for tx in recent_transactions:
        if tx.transaction_type == 'contribution':
            activity_type = 'contribution'
            desc = f"${tx.amount:.2f} contribution"
        elif tx.transaction_type == 'payout':
            activity_type = 'payout'
            desc = f"${tx.amount:.2f} payout received"
        else:
            activity_type = 'contribution'
            desc = f"${tx.amount:.2f} transaction"
        
        time_str = tx.timestamp.strftime('%b %d, %H:%M') if tx.timestamp else 'Recently'
        recent_activities.append({
            'type': activity_type,
            'description': desc,
            'time': time_str
        })
    
    milestones_achieved = []
    if my_net_savings >= 100:
        milestones_achieved.append('first_step')
    if my_net_savings >= 500:
        milestones_achieved.append('growing')
    if my_net_savings >= 1000:
        milestones_achieved.append('strong')
    if my_net_savings >= 5000:
        milestones_achieved.append('super')
    if my_net_savings >= 10000:
        milestones_achieved.append('legend')
    
    user_stats = {
        'total_contributed': float(my_contributions),
        'streak': user.contribution_streak or 0,
        'xp': user.xp or 0,
        'badges': UserBadge.query.filter_by(user_id=user.id).count(),
        'reputation': user.reputation or 0
    }
    
    return render_template('impact_visualizer.html',
                          stats=stats,
                          milestone_progress=milestone_progress,
                          milestones_achieved=milestones_achieved,
                          recent_activities=recent_activities,
                          user_stats=user_stats,
                          language=language)

@app.route('/create-group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        contribution_amount = float(request.form.get('contribution_amount'))
        contribution_frequency = request.form.get('contribution_frequency')
        tradition_id = request.form.get('tradition_id')
        require_approval = request.form.get('require_admin_approval') == 'on'
        
        group_code = secrets.token_hex(4).upper()
        
        tradition = None
        cultural_theme = 'default'
        if tradition_id and tradition_id != '':
            from models import Tradition
            tradition = Tradition.query.get(int(tradition_id))
            if tradition:
                cultural_theme = tradition.cultural_theme
        
        group = Group(
            name=name,
            description=description,
            contribution_amount=contribution_amount,
            contribution_frequency=contribution_frequency,
            group_code=group_code,
            created_by=session['user_id'],
            tradition_id=int(tradition_id) if tradition_id and tradition_id != '' else None,
            cultural_theme=cultural_theme,
            require_admin_approval=require_approval
        )
        db.session.add(group)
        db.session.flush()
        
        member = Member(user_id=session['user_id'], group_id=group.id, role='admin')
        db.session.add(member)
        db.session.commit()
        
        tradition_name = tradition.display_name if tradition else 'Savings Group'
        flash(f'{tradition_name} created successfully! Group code: {group_code}', 'success')
        return redirect(url_for('group_detail', group_id=group.id))
    
    from models import Tradition
    traditions = Tradition.query.all()
    language = session.get('language', 'en')
    t = get_all_ui_texts(language)
    languages = get_language_options()
    return render_template('create_group.html', traditions=traditions, t=t, languages=languages)

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
    
    streak_days = update_streak(member.user_id)
    xp_data = award_xp(member.user_id, 10, "contribution")
    check_challenge_progress(member.user_id)
    
    awarded_badges = check_and_award_badges(member.user_id)
    
    message_parts = ['Transaction recorded!']
    if xp_data['leveled_up']:
        message_parts.append(f"⬆️ Level {xp_data['current_level']}!")
    if streak_days > 1:
        message_parts.append(f"🔥 {streak_days}-day streak!")
    message_parts.append(f"+{xp_data['xp_awarded']} XP")
    
    if awarded_badges:
        badge_names = ', '.join([b.name for b in awarded_badges])
        for badge in awarded_badges:
            send_badge_notification(member.user.email, badge.name, badge.description)
        message_parts.append(f"🎉 Badges: {badge_names}")
    
    flash(' '.join(message_parts), 'success')
    
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
    
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    return render_template('admin_dashboard.html', 
                          pending_approvals=pending_approvals,
                          admin_groups=admin_groups,
                          proverb=proverb,
                          language=language)

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

def calculate_reputation_score(user_id):
    """Calculate user reputation score (0-100) based on activity"""
    user = User.query.get(user_id)
    if not user:
        return {'total': 0, 'consistency': 0, 'activity': 0}
    
    memberships = Member.query.filter_by(user_id=user_id, is_active=True, is_ghost=False).all()
    
    if not memberships:
        return {'total': 0, 'consistency': 0, 'activity': 0}
    
    consistency_score = 0
    activity_score = 0
    
    for membership in memberships:
        if membership.reliability_score:
            consistency_score += membership.reliability_score
    
    consistency_score = min(100, consistency_score // len(memberships))
    
    member_ids = [m.id for m in memberships]
    total_contributions = Transaction.query.filter(
        Transaction.member_id.in_(member_ids),
        Transaction.transaction_type == 'contribution'
    ).count()
    
    activity_score = min(100, total_contributions * 5)
    
    total_score = int((consistency_score * 0.6) + (activity_score * 0.4))
    
    return {
        'total': total_score,
        'consistency': consistency_score,
        'activity': activity_score
    }

@app.route('/my-badges')
@login_required
def my_badges():
    user = User.query.get(session['user_id'])
    user_badges = UserBadge.query.filter_by(user_id=user.id).all()
    all_badges = Badge.query.all()
    
    earned_badge_ids = [ub.badge_id for ub in user_badges]
    
    reputation_data = calculate_reputation_score(user.id)
    
    advice = get_financial_advice(user.id)
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    
    newly_earned = request.args.get('new_badge', False)
    
    return render_template('badges.html', 
                          user_badges=user_badges,
                          all_badges=all_badges,
                          earned_badge_ids=earned_badge_ids,
                          reputation_score=reputation_data['total'],
                          consistency_score=reputation_data['consistency'],
                          activity_score=reputation_data['activity'],
                          advice=advice,
                          proverb=proverb,
                          language=language,
                          newly_earned_badge=newly_earned)

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

@app.route('/leaderboard')
@login_required
def leaderboard():
    from models import UserXP
    from sqlalchemy.orm import joinedload
    
    try:
        top_users = UserXP.query.options(
            joinedload(UserXP.user)
        ).order_by(UserXP.total_xp.desc()).limit(50).all()
        
        current_user_xp = UserXP.query.filter_by(user_id=session['user_id']).first()
        rank_data = get_user_rank(session['user_id'])
        
        return render_template('leaderboard.html',
                              top_users=top_users,
                              current_user_xp=current_user_xp,
                              rank_data=rank_data)
    except Exception as e:
        flash('Leaderboard features not yet initialized. Run database migrations first.', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/initialize-beta-features', methods=['POST'])
@login_required
def initialize_beta_features():
    """Initialize beta features for current user"""
    from models import UserXP
    
    user_xp = UserXP.query.filter_by(user_id=session['user_id']).first()
    if not user_xp:
        user_xp = UserXP(user_id=session['user_id'], total_xp=0, current_level=1)
        db.session.add(user_xp)
        db.session.commit()
    
    fetch_exchange_rates()
    
    flash('Beta features initialized! Check out the leaderboard and your XP progress.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/initialize-traditions', methods=['POST'])
@login_required
def initialize_traditions():
    """Initialize cultural savings traditions in the database"""
    from traditions_data import seed_traditions
    try:
        seed_traditions()
        flash('Cultural traditions initialized successfully! Create a group and choose your tradition.', 'success')
    except Exception as e:
        flash(f'Error initializing traditions: {str(e)}', 'danger')
    return redirect(url_for('create_group'))

@app.route('/financial-survey', methods=['GET'])
@login_required
def financial_survey():
    """Display financial survey questionnaire"""
    from models import UserFinancialProfile
    
    existing_profile = UserFinancialProfile.query.filter_by(user_id=session['user_id']).first()
    if existing_profile:
        flash('You have already completed the financial survey. View your recommendations below.', 'info')
        return redirect(url_for('survey_results'))
    
    return render_template('financial_survey.html')

@app.route('/submit-financial-survey', methods=['POST'])
@login_required
def submit_financial_survey():
    """Process financial survey and create user profile"""
    from models import UserFinancialProfile
    
    has_emergency_fund_value = request.form.get('has_emergency_fund')
    has_emergency_fund = has_emergency_fund_value == 'yes'
    
    profile = UserFinancialProfile(
        user_id=session['user_id'],
        income_range=request.form.get('income_range'),
        savings_habit=request.form.get('savings_habit'),
        financial_goal=request.form.get('financial_goal'),
        risk_tolerance=request.form.get('risk_tolerance'),
        employment_status=request.form.get('employment_status'),
        dependents=int(request.form.get('dependents', 0)),
        has_emergency_fund=has_emergency_fund,
        preferred_group_size=request.form.get('preferred_group_size'),
        contribution_comfort_level=request.form.get('contribution_comfort_level')
    )
    
    db.session.add(profile)
    db.session.commit()
    
    flash('Thank you! Your financial profile has been saved. Here are your personalized recommendations.', 'success')
    return redirect(url_for('survey_results'))

@app.route('/survey-results')
@login_required
def survey_results():
    """Display personalized group recommendations based on survey"""
    from models import UserFinancialProfile, Tradition
    
    profile = UserFinancialProfile.query.filter_by(user_id=session['user_id']).first()
    
    if not profile:
        flash('Please complete the financial survey first to get personalized recommendations.', 'warning')
        return redirect(url_for('financial_survey'))
    
    recommended_groups = Group.query.filter(
        Group.id.in_(
            db.session.query(Member.group_id)
            .filter(Member.user_id != session['user_id'])
            .distinct()
        )
    ).limit(10).all()
    
    contribution_ranges = {
        'under_50': (0, 50),
        '50_100': (50, 100),
        '100_250': (100, 250),
        '250_500': (250, 500),
        'over_500': (500, 10000)
    }
    
    min_amount, max_amount = contribution_ranges.get(profile.contribution_comfort_level, (0, 10000))
    
    matched_groups = []
    for group in recommended_groups:
        if min_amount <= group.contribution_amount <= max_amount:
            matched_groups.append(group)
    
    traditions = Tradition.query.all()
    
    insights = generate_financial_insights(profile)
    
    return render_template('survey_results.html',
                          profile=profile,
                          matched_groups=matched_groups[:5],
                          traditions=traditions,
                          insights=insights)

def generate_financial_insights(profile):
    """Generate personalized financial insights based on survey responses"""
    insights = {
        'recommended_contribution': '',
        'group_size_recommendation': '',
        'savings_tips': [],
        'risk_assessment': ''
    }
    
    income_recommendations = {
        'under_1000': '$25-50',
        '1000_2500': '$50-100',
        '2500_5000': '$100-250',
        '5000_7500': '$250-500',
        '7500_10000': '$500-750',
        'over_10000': '$750+'
    }
    insights['recommended_contribution'] = income_recommendations.get(profile.income_range, '$50-100')
    
    size_recs = {
        'small': 'Small groups (5-10 members) offer more intimacy and easier coordination.',
        'medium': 'Medium groups (11-20 members) provide balanced community and diversity.',
        'large': 'Large groups (21+ members) offer bigger savings pools and networking opportunities.',
        'no_preference': 'Consider starting with a medium-sized group to balance community and manageability.'
    }
    insights['group_size_recommendation'] = size_recs.get(profile.preferred_group_size, size_recs['no_preference'])
    
    if not profile.has_emergency_fund:
        insights['savings_tips'].append('Priority: Build an emergency fund covering 3-6 months of expenses before aggressive savings.')
    
    if profile.savings_habit in ['none', 'occasional']:
        insights['savings_tips'].append('Start small: Even $25/month builds the habit. Automate your savings for consistency.')
    
    if profile.financial_goal == 'debt_payoff':
        insights['savings_tips'].append('Consider the debt avalanche method: Pay minimums on all debts, extra on highest interest rate.')
    
    if profile.financial_goal == 'business':
        insights['savings_tips'].append('Business savings groups can provide both capital and networking. Look for entrepreneur-focused groups.')
    
    risk_levels = {
        'very_low': 'Your conservative approach is wise. Stick to traditional savings groups with proven track records.',
        'low': 'You prefer stability. Look for groups with established rules and reliable members.',
        'moderate': 'Your balanced risk tolerance opens many options. Explore various group types.',
        'high': 'You can handle volatility. Consider innovative group structures or investment-focused circles.'
    }
    insights['risk_assessment'] = risk_levels.get(profile.risk_tolerance, risk_levels['moderate'])
    
    return insights

@app.route('/group/<int:group_id>/add-ghost-user', methods=['POST'])
@login_required
def add_ghost_user(group_id):
    """Add a ghost (placeholder) user to a group for balanced rotations"""
    from models import Member
    import uuid
    
    group = Group.query.get_or_404(group_id)
    membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id).first()
    
    if not membership or membership.role != 'admin':
        flash('Only group admins can add ghost users.', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    ghost_name = request.form.get('ghost_name', 'Placeholder')
    ghost_uuid = str(uuid.uuid4())[:8]
    
    ghost_user = User(
        username=f"ghost-{ghost_uuid}",
        email=f"ghost-{ghost_uuid}@tikob.internal",
        is_ghost=True,
        notification_enabled=False
    )
    ghost_user.set_password(str(uuid.uuid4()))
    
    db.session.add(ghost_user)
    db.session.flush()
    
    ghost_member = Member(
        user_id=ghost_user.id,
        group_id=group_id,
        role='member',
        is_active=True,
        is_ghost=True,
        reliability_score=0,
        approval_status='approved'
    )
    
    db.session.add(ghost_member)
    db.session.commit()
    
    flash(f'Ghost user "{ghost_name}" added successfully. You can use this for rotation balancing.', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/group/<int:group_id>/remove-ghost/<int:member_id>', methods=['POST'])
@login_required
def remove_ghost_user(group_id, member_id):
    """Remove a ghost user from a group"""
    from models import Member
    
    group = Group.query.get_or_404(group_id)
    admin_membership = Member.query.filter_by(user_id=session['user_id'], group_id=group_id).first()
    
    if not admin_membership or admin_membership.role != 'admin':
        flash('Only group admins can remove ghost users.', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    ghost_member = Member.query.get_or_404(member_id)
    
    if not ghost_member.is_ghost:
        flash('This is not a ghost user.', 'danger')
        return redirect(url_for('group_detail', group_id=group_id))
    
    db.session.delete(ghost_member)
    db.session.commit()
    
    flash('Ghost user removed successfully.', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/plaid/create-link-token', methods=['POST'])
@login_required
def create_plaid_link_token():
    """Create Plaid Link token for bank account linking"""
    try:
        import plaid
        from plaid.api import plaid_api
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.products import Products
        from plaid.model.country_code import CountryCode
        import os
        
        plaid_client_id = os.getenv('PLAID_CLIENT_ID')
        plaid_secret = os.getenv('PLAID_SECRET')
        plaid_env = os.getenv('PLAID_ENV', 'sandbox')
        
        if not plaid_client_id or not plaid_secret:
            return jsonify({'error': 'Plaid API keys not configured'}), 400
        
        host = plaid.Environment.Sandbox if plaid_env == 'sandbox' else plaid.Environment.Production
        
        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': plaid_client_id,
                'secret': plaid_secret,
                'plaidVersion': '2020-09-14'
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        client = plaid_api.PlaidApi(api_client)
        
        link_request = LinkTokenCreateRequest(
            products=[Products('transactions'), Products('auth')],
            client_name="TiKòb - Community Savings",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(session['user_id'])
            )
        )
        
        response = client.link_token_create(link_request)
        return jsonify(response.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/plaid/exchange-token', methods=['POST'])
@login_required
def exchange_plaid_token():
    """Exchange Plaid public token for access token"""
    try:
        import plaid
        from plaid.api import plaid_api
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
        from models import PlaidAccount
        import os
        
        public_token = request.json.get('public_token')
        institution_name = request.json.get('institution_name', 'Bank')
        
        if not public_token:
            return jsonify({'error': 'Public token required'}), 400
        
        plaid_client_id = os.getenv('PLAID_CLIENT_ID')
        plaid_secret = os.getenv('PLAID_SECRET')
        plaid_env = os.getenv('PLAID_ENV', 'sandbox')
        
        host = plaid.Environment.Sandbox if plaid_env == 'sandbox' else plaid.Environment.Production
        
        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': plaid_client_id,
                'secret': plaid_secret,
                'plaidVersion': '2020-09-14'
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        client = plaid_api.PlaidApi(api_client)
        
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        
        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']
        
        plaid_account = PlaidAccount(
            user_id=session['user_id'],
            access_token=access_token,
            item_id=item_id,
            institution_name=institution_name,
            is_active=True
        )
        
        db.session.add(plaid_account)
        db.session.commit()
        
        flash(f'Bank account linked successfully to {institution_name}!', 'success')
        return jsonify({'success': True, 'item_id': item_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/money-management')
@login_required
def money_management():
    """Personal money management dashboard"""
    from models import PlaidAccount, PersonalTransaction
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    plaid_accounts = PlaidAccount.query.filter_by(user_id=session['user_id'], is_active=True).all()
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_transactions = PersonalTransaction.query.filter(
        PersonalTransaction.user_id == session['user_id'],
        PersonalTransaction.transaction_date >= thirty_days_ago
    ).order_by(PersonalTransaction.transaction_date.desc()).limit(50).all()
    
    total_income = db.session.query(func.sum(PersonalTransaction.amount)).filter(
        PersonalTransaction.user_id == session['user_id'],
        PersonalTransaction.is_income == True,
        PersonalTransaction.transaction_date >= thirty_days_ago
    ).scalar() or 0
    
    total_expenses = db.session.query(func.sum(PersonalTransaction.amount)).filter(
        PersonalTransaction.user_id == session['user_id'],
        PersonalTransaction.is_income == False,
        PersonalTransaction.transaction_date >= thirty_days_ago
    ).scalar() or 0
    
    net_savings = total_income - total_expenses
    
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    
    return render_template('money_management.html',
                          plaid_accounts=plaid_accounts,
                          recent_transactions=recent_transactions,
                          total_income=total_income,
                          total_expenses=total_expenses,
                          net_savings=net_savings,
                          proverb=proverb)

@app.route('/set-language/<lang>')
def set_language(lang):
    """Set language - works for logged in and guest users"""
    if lang in SUPPORTED_LANGUAGES:
        session['language'] = lang
        if 'user_id' in session:
            flash(get_community_phrase('welcome', lang if lang in ['en', 'ht'] else 'en'), 'success')
    return redirect(request.referrer or url_for('login'))

@app.route('/group/<int:group_id>/chat')
@login_required
def group_chat(group_id):
    """Folkloric group chat page"""
    group = Group.query.get_or_404(group_id)
    member = Member.query.filter_by(group_id=group_id, user_id=session['user_id'], is_active=True).first()
    
    if not member:
        flash('You must be a member to access this group chat.', 'danger')
        return redirect(url_for('dashboard'))
    
    messages = GroupMessage.query.filter_by(group_id=group_id).order_by(GroupMessage.created_at.asc()).limit(100).all()
    members = Member.query.filter_by(group_id=group_id, is_active=True).all()
    
    language = session.get('language', 'en')
    proverbs = [
        get_random_proverb(language),
        "Unity is strength, division is weakness.",
        "Little by little fills the measure.",
        "Many hands make light work."
    ]
    
    tradition_name = group.tradition.display_name if group.tradition else "Community"
    tradition_icon = group.tradition.icon if group.tradition else "🌍"
    
    return render_template('group_chat.html',
                          group=group,
                          messages=messages,
                          members=members,
                          proverbs=proverbs,
                          tradition_name=tradition_name,
                          tradition_icon=tradition_icon,
                          current_user_id=session['user_id'])

@app.route('/api/random-proverb')
@login_required
def random_proverb_api():
    """API endpoint for random proverbs"""
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    return jsonify({'proverb': proverb})

@app.route('/api/ai-proverb')
def ai_proverb_api():
    """API endpoint for AI-generated Haitian proverbs - works without login"""
    try:
        language = session.get('language', 'en')
        proverb_data = generate_haitian_proverb()
        
        if language == 'ht':
            return jsonify({
                'proverb': {
                    'text': proverb_data['creole'],
                    'meaning': proverb_data['english']
                }
            })
        else:
            return jsonify({
                'proverb': {
                    'text': proverb_data['english'],
                    'meaning': proverb_data['meaning'] or proverb_data['creole']
                }
            })
    except Exception as e:
        print(f"AI proverb error: {e}")
        return jsonify({'proverb': {'text': 'Many hands make the load lighter', 'meaning': 'Together we are stronger'}})

@socketio.on('join_group')
def on_join_group(data):
    """Join a group's chat room"""
    group_id = data.get('group_id')
    if group_id:
        join_room(f'group_{group_id}')
        emit('message', {'msg': 'Welcome to the story circle!'}, room=request.sid)

@socketio.on('send_message')
def on_send_message(data):
    """Handle new messages"""
    if 'user_id' not in session:
        return
    
    group_id = data.get('group_id')
    content = data.get('content')
    is_proverb = data.get('is_proverb', False)
    proverb_context = data.get('proverb_context')
    
    if group_id and content:
        user = User.query.get(session['user_id'])
        member = Member.query.filter_by(group_id=group_id, user_id=session['user_id']).first()
        
        if user and member:
            message = GroupMessage(
                group_id=group_id,
                user_id=session['user_id'],
                content=content,
                is_proverb=is_proverb,
                proverb_context=proverb_context
            )
            db.session.add(message)
            db.session.commit()
            
            emit('new_message', {
                'group_id': group_id,
                'message_id': message.id,
                'username': user.username,
                'content': content,
                'is_proverb': is_proverb,
                'proverb_context': proverb_context,
                'is_storyteller': member.is_storyteller,
                'created_at': message.created_at.isoformat()
            }, room=f'group_{group_id}')

@socketio.on('add_reaction')
def on_add_reaction(data):
    """Handle message reactions"""
    if 'user_id' not in session:
        return
    
    message_id = data.get('message_id')
    emoji = data.get('emoji')
    
    if message_id and emoji:
        existing = MessageReaction.query.filter_by(
            message_id=message_id,
            user_id=session['user_id'],
            emoji=emoji
        ).first()
        
        if not existing:
            reaction = MessageReaction(
                message_id=message_id,
                user_id=session['user_id'],
                emoji=emoji
            )
            db.session.add(reaction)
            db.session.commit()

@app.route('/api/v1/deposits', methods=['POST'])
@login_required
@csrf.exempt
def api_deposit():
    """Record a member deposit via double-entry ledger"""
    try:
        data = request.get_json()
        member_id = data.get('memberId') or session['user_id']
        group_id = data.get('groupId')
        amount = Decimal(str(data.get('amount', 0)))
        ref = data.get('ref', f'deposit_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}')
        
        if not group_id or amount <= 0:
            return jsonify({'error': 'Invalid group_id or amount'}), 400
        
        event = LedgerService.record_deposit(
            member_id=member_id,
            group_id=group_id,
            amount=amount,
            ref=ref,
            created_by=session['user_id']
        )
        
        return jsonify({
            'success': True,
            'eventId': event.id,
            'message': 'Deposit recorded successfully'
        })
    except LedgerError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/withdrawals', methods=['POST'])
@login_required
@csrf.exempt
def api_withdrawal():
    """Record a member withdrawal via double-entry ledger"""
    try:
        data = request.get_json()
        member_id = data.get('memberId') or session['user_id']
        group_id = data.get('groupId')
        amount = Decimal(str(data.get('amount', 0)))
        ref = data.get('ref', f'withdrawal_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}')
        
        if not group_id or amount <= 0:
            return jsonify({'error': 'Invalid group_id or amount'}), 400
        
        event = LedgerService.record_withdrawal(
            member_id=member_id,
            group_id=group_id,
            amount=amount,
            ref=ref,
            created_by=session['user_id']
        )
        
        return jsonify({
            'success': True,
            'eventId': event.id,
            'message': 'Withdrawal recorded successfully'
        })
    except LedgerError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/interest/accrue', methods=['POST'])
@login_required
@csrf.exempt
def api_accrue_interest():
    """Accrue interest across members using time-weighted allocation"""
    try:
        data = request.get_json()
        group_id = data.get('groupId')
        accrual_date = date.fromisoformat(data.get('date', date.today().isoformat()))
        total_interest = Decimal(str(data.get('totalInterest', 0)))
        ref = data.get('ref', f'interest_{accrual_date.isoformat()}')
        
        if not group_id or total_interest <= 0:
            return jsonify({'error': 'Invalid group_id or totalInterest'}), 400
        
        event = LedgerService.accrue_interest(
            group_id=group_id,
            accrual_date=accrual_date,
            total_interest=total_interest,
            ref=ref
        )
        
        return jsonify({
            'success': True,
            'eventId': event.id,
            'message': 'Interest accrued successfully'
        })
    except LedgerError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/members/<int:member_id>/positions/<int:group_id>')
@login_required
def api_member_position(member_id, group_id):
    """Get member's financial position"""
    try:
        position = LedgerService.get_member_position(member_id, group_id)
        return jsonify(position)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/groups/<int:group_id>/balance')
@login_required
def api_group_balance(group_id):
    """Get group's pool balance"""
    try:
        balance = LedgerService.get_pool_balance(group_id)
        return jsonify({
            'groupId': group_id,
            'poolBalance': float(balance)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reconcile/<int:group_id>')
@login_required
def api_reconcile(group_id):
    """Run reconciliation check for a group"""
    try:
        results = ReconciliationService.run_full_reconciliation(group_id)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reports/<int:member_id>/<int:year>/statement', methods=['POST'])
@login_required
@csrf.exempt
def api_generate_statement(member_id, year):
    """Generate year-to-date statement"""
    try:
        data = request.get_json() or {}
        group_id = data.get('groupId')
        
        report = TaxReportService.generate_statement(member_id, group_id, year)
        
        return jsonify({
            'success': True,
            'reportId': report.id,
            'payload': report.payload,
            'checksum': report.checksum
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reports/<int:member_id>/<int:year>/1099-int', methods=['POST'])
@login_required
@csrf.exempt
def api_generate_1099(member_id, year):
    """Generate 1099-INT report"""
    try:
        data = request.get_json()
        payer_info = data.get('payerInfo', {
            'name': 'TiKòb Community Savings',
            'tin': 'XX-XXXXXXX',
            'address': 'Community Savings Platform'
        })
        
        report = TaxReportService.generate_1099_int(member_id, year, payer_info)
        
        return jsonify({
            'success': True,
            'reportId': report.id,
            'payload': report.payload,
            'checksum': report.checksum
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reports/<report_id>/finalize', methods=['POST'])
@login_required
@csrf.exempt
def api_finalize_report(report_id):
    """Finalize a report (no further edits)"""
    try:
        report = TaxReportService.finalize_report(report_id)
        return jsonify({
            'success': True,
            'reportId': report.id,
            'status': report.status,
            'finalizedAt': report.finalized_at.isoformat()
        })
    except LedgerError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.context_processor
def utility_processor():
    """Make utility functions available to all templates"""
    from traditions_data import get_tradition_theme_colors
    return {
        'get_user_initials': get_user_initials,
        'get_avatar_color': get_avatar_color,
        'get_community_phrase': get_community_phrase,
        'get_tradition_theme_colors': get_tradition_theme_colors
    }

# ============== TELLER BANK LINKING ==============
TELLER_APP_ID = os.environ.get('TELLER_APP_ID')
TELLER_ENVIRONMENT = os.environ.get('TELLER_ENVIRONMENT', 'sandbox')
AUDIO_UPLOAD_FOLDER = 'app/uploads/audio'
os.makedirs(AUDIO_UPLOAD_FOLDER, exist_ok=True)

@app.route('/bank-linking')
@login_required
def bank_linking():
    """Bank account linking page with Teller Connect"""
    user_id = session.get('user_id')
    linked_accounts = TellerAccount.query.filter_by(user_id=user_id, is_active=True).all()
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    return render_template('bank_linking.html', 
                          teller_app_id=TELLER_APP_ID,
                          teller_environment=TELLER_ENVIRONMENT,
                          linked_accounts=linked_accounts,
                          language=language,
                          proverb=proverb)

@app.route('/api/teller/save-enrollment', methods=['POST'])
@login_required
@csrf.exempt
def save_teller_enrollment():
    """Save Teller enrollment after successful bank connection"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        access_token = data.get('accessToken')
        enrollment = data.get('enrollment', {})
        
        if not access_token or not enrollment:
            return jsonify({'error': 'Missing enrollment data'}), 400
        
        existing = TellerAccount.query.filter_by(
            user_id=user_id, 
            enrollment_id=enrollment.get('id')
        ).first()
        
        if existing:
            existing.access_token = access_token
            existing.last_synced = datetime.utcnow()
            db.session.commit()
            return jsonify({'success': True, 'message': 'Account updated'})
        
        new_account = TellerAccount(
            user_id=user_id,
            access_token=access_token,
            enrollment_id=enrollment.get('id'),
            institution_name=enrollment.get('institution', {}).get('name'),
            institution_id=enrollment.get('institution', {}).get('id'),
            last_synced=datetime.utcnow()
        )
        db.session.add(new_account)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Bank account linked successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/teller/accounts')
@login_required
def get_teller_accounts():
    """Get user's linked Teller accounts"""
    user_id = session.get('user_id')
    accounts = TellerAccount.query.filter_by(user_id=user_id, is_active=True).all()
    return jsonify({
        'accounts': [{
            'id': acc.id,
            'institution_name': acc.institution_name,
            'account_name': acc.account_name or 'Primary Account',
            'account_type': acc.account_type or 'checking',
            'last_four': acc.last_four,
            'last_synced': acc.last_synced.isoformat() if acc.last_synced else None
        } for acc in accounts]
    })

@app.route('/api/teller/disconnect/<int:account_id>', methods=['POST'])
@login_required
@csrf.exempt
def disconnect_teller_account(account_id):
    """Disconnect a linked bank account"""
    user_id = session.get('user_id')
    account = TellerAccount.query.filter_by(id=account_id, user_id=user_id).first()
    if account:
        account.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Account disconnected'})
    return jsonify({'error': 'Account not found'}), 404

# ============== AUDIO MESSAGING ==============
ALLOWED_AUDIO_EXTENSIONS = {'webm', 'mp3', 'wav', 'ogg', 'm4a'}

def allowed_audio_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

@app.route('/api/audio/upload', methods=['POST'])
@login_required
@csrf.exempt
def upload_audio():
    """Upload audio message"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        ext = audio_file.filename.rsplit('.', 1)[1].lower() if '.' in audio_file.filename else 'webm'
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            ext = 'webm'
        
        filename = f"audio_{session.get('user_id')}_{int(time.time())}_{secrets.token_hex(4)}.{ext}"
        filepath = os.path.join(AUDIO_UPLOAD_FOLDER, filename)
        audio_file.save(filepath)
        
        audio_url = url_for('serve_audio', filename=filename, _external=False)
        return jsonify({'success': True, 'audio_url': audio_url, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/audio/<filename>')
def serve_audio(filename):
    """Serve uploaded audio files"""
    return send_file(os.path.join('uploads/audio', filename))

@socketio.on('send_audio_message')
def on_send_audio_message(data):
    """Handle audio message via WebSocket"""
    user_id = session.get('user_id')
    group_id = data.get('group_id')
    audio_url = data.get('audio_url')
    duration = data.get('duration', 0)
    
    if user_id and group_id and audio_url:
        user = User.query.get(user_id)
        member = Member.query.filter_by(user_id=user_id, group_id=group_id, is_active=True).first()
        
        if member:
            message = GroupMessage(
                group_id=group_id,
                user_id=user_id,
                content='[Voice Message]',
                message_type='audio',
                audio_url=audio_url,
                audio_duration=duration
            )
            db.session.add(message)
            db.session.commit()
            
            emit('new_audio_message', {
                'group_id': group_id,
                'message_id': message.id,
                'username': user.username,
                'audio_url': audio_url,
                'duration': duration,
                'is_storyteller': member.is_storyteller,
                'created_at': message.created_at.isoformat()
            }, room=f'group_{group_id}')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
