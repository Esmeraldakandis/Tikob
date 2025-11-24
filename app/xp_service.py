from models import db, UserXP, Transaction, UserChallenge, Challenge
from datetime import datetime, timedelta
from notifications import send_badge_notification

XP_PER_CONTRIBUTION = 10
XP_PER_LEVEL = 100

def award_xp(user_id, xp_amount, reason="contribution"):
    """Award XP to user and check for level up"""
    user_xp = UserXP.query.filter_by(user_id=user_id).first()
    
    if not user_xp:
        user_xp = UserXP(user_id=user_id, total_xp=0, current_level=1, current_streak=0)
        db.session.add(user_xp)
    
    user_xp.total_xp += xp_amount
    new_level = (user_xp.total_xp // XP_PER_LEVEL) + 1
    
    leveled_up = new_level > user_xp.current_level
    user_xp.current_level = new_level
    
    db.session.commit()
    
    return {
        'xp_awarded': xp_amount,
        'total_xp': user_xp.total_xp,
        'current_level': user_xp.current_level,
        'leveled_up': leveled_up,
        'xp_to_next_level': XP_PER_LEVEL - (user_xp.total_xp % XP_PER_LEVEL)
    }

def update_streak(user_id):
    """Update contribution streak for user"""
    user_xp = UserXP.query.filter_by(user_id=user_id).first()
    
    if not user_xp:
        user_xp = UserXP(user_id=user_id, total_xp=0, current_level=1, current_streak=1)
        user_xp.last_contribution_date = datetime.utcnow()
        db.session.add(user_xp)
        db.session.commit()
        return 1
    
    now = datetime.utcnow()
    last_contribution = user_xp.last_contribution_date
    
    if last_contribution:
        days_diff = (now - last_contribution).days
        
        if days_diff == 1:
            user_xp.current_streak += 1
        elif days_diff > 1:
            user_xp.current_streak = 1
    else:
        user_xp.current_streak = 1
    
    if user_xp.current_streak > user_xp.longest_streak:
        user_xp.longest_streak = user_xp.current_streak
    
    user_xp.last_contribution_date = now
    
    streak_bonus_xp = min(user_xp.current_streak * 2, 50)
    user_xp.total_xp += streak_bonus_xp
    
    db.session.commit()
    
    return user_xp.current_streak

def get_user_rank(user_id):
    """Get user's rank based on total XP"""
    all_users = UserXP.query.order_by(UserXP.total_xp.desc()).all()
    
    for idx, user_xp in enumerate(all_users, 1):
        if user_xp.user_id == user_id:
            return {
                'rank': idx,
                'total_users': len(all_users),
                'percentile': ((len(all_users) - idx) / len(all_users)) * 100 if len(all_users) > 0 else 0
            }
    
    return {'rank': 0, 'total_users': len(all_users), 'percentile': 0}

def check_challenge_progress(user_id):
    """Check and update challenge progress"""
    user_challenges = UserChallenge.query.filter_by(user_id=user_id, completed=False).all()
    
    completed_challenges = []
    
    for uc in user_challenges:
        challenge = uc.challenge
        
        if challenge.challenge_type == 'contribution_count':
            contribution_count = Transaction.query.join(Transaction.member).filter(
                Transaction.member.has(user_id=user_id),
                Transaction.transaction_type == 'contribution'
            ).count()
            
            uc.progress = contribution_count
            
            if contribution_count >= challenge.target_value:
                uc.completed = True
                uc.completed_date = datetime.utcnow()
                award_xp(user_id, challenge.xp_reward, "challenge_completion")
                completed_challenges.append(challenge)
        
        elif challenge.challenge_type == 'streak':
            user_xp = UserXP.query.filter_by(user_id=user_id).first()
            if user_xp and user_xp.current_streak >= challenge.target_value:
                uc.completed = True
                uc.completed_date = datetime.utcnow()
                award_xp(user_id, challenge.xp_reward, "challenge_completion")
                completed_challenges.append(challenge)
    
    db.session.commit()
    
    return completed_challenges
