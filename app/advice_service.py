from models import db, PersonalizedAdvice, Transaction, UserXP, FinancialGoal, Member
from datetime import datetime, timedelta
import random
from sqlalchemy import func

def generate_personalized_advice(user_id):
    """Generate context-aware financial advice based on user behavior"""
    
    contributions = Transaction.query.join(Transaction.member).filter(
        Transaction.member.has(user_id=user_id),
        Transaction.transaction_type == 'contribution'
    ).all()
    
    total_saved = sum(t.amount for t in contributions)
    recent_contributions = [t for t in contributions if t.transaction_date > datetime.utcnow() - timedelta(days=30)]
    
    advice_list = []
    
    if len(contributions) == 0:
        advice_list.append({
            'text': "🌟 Start your savings journey today! Making your first contribution is the hardest step, but also the most rewarding.",
            'type': 'motivation',
            'priority': 10
        })
    
    elif len(recent_contributions) == 0:
        advice_list.append({
            'text': f"💪 You've saved ${total_saved:.2f} so far - great work! But we haven't seen you contribute in 30 days. Get back on track today!",
            'type': 'engagement',
            'priority': 9
        })
    
    elif len(recent_contributions) >= 4:
        advice_list.append({
            'text': f"🔥 You're on fire! {len(recent_contributions)} contributions this month. Keep this momentum going!",
            'type': 'celebration',
            'priority': 8
        })
    
    user_xp = UserXP.query.filter_by(user_id=user_id).first()
    if user_xp:
        if user_xp.current_streak >= 7:
            advice_list.append({
                'text': f"⚡ Amazing {user_xp.current_streak}-day streak! You're building incredible financial discipline.",
                'type': 'streak_celebration',
                'priority': 9
            })
        elif user_xp.current_streak >= 3:
            advice_list.append({
                'text': f"📈 {user_xp.current_streak}-day streak! Keep going to unlock bonus XP at day 7.",
                'type': 'streak_motivation',
                'priority': 7
            })
    
    active_goals = FinancialGoal.query.filter_by(user_id=user_id, achieved=False).all()
    for goal in active_goals:
        progress_pct = (goal.current_amount / goal.target_amount) * 100 if goal.target_amount > 0 else 0
        
        if progress_pct >= 75:
            advice_list.append({
                'text': f"🎯 You're {progress_pct:.0f}% toward your '{goal.goal_name}' goal! Just ${goal.target_amount - goal.current_amount:.2f} to go!",
                'type': 'goal_progress',
                'priority': 10
            })
        elif progress_pct >= 50:
            advice_list.append({
                'text': f"👍 Halfway there on '{goal.goal_name}'! You've got this!",
                'type': 'goal_progress',
                'priority': 7
            })
    
    if total_saved >= 1000:
        advice_list.append({
            'text': f"💰 You've saved over $1,000! Consider diversifying into an emergency fund or investment account.",
            'type': 'strategic',
            'priority': 6
        })
    
    avg_contribution = sum(t.amount for t in recent_contributions) / len(recent_contributions) if recent_contributions else 0
    if avg_contribution > 0:
        weekly_projection = avg_contribution * 52 / 12
        advice_list.append({
            'text': f"📊 At your current pace (${avg_contribution:.2f}/contribution), you'll save ~${weekly_projection:.2f} per month!",
            'type': 'insights',
            'priority': 5
        })
    
    general_tips = [
        {"text": "💡 The 50/30/20 rule: 50% needs, 30% wants, 20% savings. Are you on track?", "type": "education", "priority": 4},
        {"text": "🏦 Build an emergency fund covering 3-6 months of expenses for financial security.", "type": "education", "priority": 4},
        {"text": "📱 Automate your savings! Set up recurring contributions to make saving effortless.", "type": "strategy", "priority": 4},
        {"text": "🎯 Set specific, measurable financial goals. Vague goals rarely get achieved!", "type": "strategy", "priority": 4}
    ]
    
    advice_list.extend(general_tips)
    
    advice_list.sort(key=lambda x: x['priority'], reverse=True)
    
    if advice_list:
        top_advice = advice_list[0]
        
        personalized_advice = PersonalizedAdvice(
            user_id=user_id,
            advice_text=top_advice['text'],
            advice_type=top_advice['type'],
            context_data=f"total_saved: {total_saved}, recent_contributions: {len(recent_contributions)}",
            displayed=False
        )
        db.session.add(personalized_advice)
        db.session.commit()
        
        return top_advice['text']
    
    return "Keep saving consistently - your future self will thank you!"

def get_latest_advice(user_id):
    """Get the latest undisplayed advice for user"""
    advice = PersonalizedAdvice.query.filter_by(
        user_id=user_id,
        displayed=False
    ).order_by(PersonalizedAdvice.created_at.desc()).first()
    
    if advice:
        advice.displayed = True
        db.session.commit()
        return advice.advice_text
    
    return generate_personalized_advice(user_id)
