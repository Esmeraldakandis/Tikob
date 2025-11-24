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
from xp_service import award_xp, update_streak, get_user_rank, check_challenge_progress
from advice_service import get_latest_advice
from currency_service import fetch_exchange_rates, convert_amount, get_user_currency, format_currency
from haitian_culture import get_random_proverb, get_financial_wisdom, get_community_phrase
from avatar_helper import get_user_initials, get_avatar_color
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
    
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    advice = get_financial_advice(user.id)
    recent_badges = UserBadge.query.options(joinedload(UserBadge.badge)).filter_by(
        user_id=user.id
    ).order_by(UserBadge.earned_at.desc()).limit(3).all()
    
    return render_template('dashboard.html', 
                          groups_data=groups_data, 
                          proverb=proverb,
                          advice=advice,
                          recent_badges=recent_badges,
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
    return render_template('create_group.html', traditions=traditions)

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

@app.route('/my-badges')
@login_required
def my_badges():
    user = User.query.get(session['user_id'])
    user_badges = UserBadge.query.filter_by(user_id=user.id).all()
    all_badges = Badge.query.all()
    
    earned_badge_ids = [ub.badge_id for ub in user_badges]
    
    advice = get_financial_advice(user.id)
    language = session.get('language', 'en')
    proverb = get_random_proverb(language)
    
    return render_template('badges.html', 
                          user_badges=user_badges,
                          all_badges=all_badges,
                          earned_badge_ids=earned_badge_ids,
                          advice=advice,
                          proverb=proverb,
                          language=language)

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
@login_required
def set_language(lang):
    if lang in ['en', 'ht']:
        session['language'] = lang
        flash(get_community_phrase('welcome', lang), 'success')
    return redirect(request.referrer or url_for('dashboard'))

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
