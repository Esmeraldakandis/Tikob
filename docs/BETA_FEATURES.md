# TiKòb Beta Features - Technical Design

## Overview
This document outlines the technical architecture and implementation plan for three major beta features planned for TiKòb Phase 2.

---

## Feature 1: Dynamic Financial Advice System

### Current State
- Static motivational quotes displayed randomly
- 6 predefined financial tips in database
- No personalization or user context

### Beta Enhancement
Personalized, context-aware financial advice based on user behavior, savings patterns, and goals.

### Architecture

#### Database Schema Changes
```sql
CREATE TABLE financial_goals (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    goal_name VARCHAR(200),
    target_amount DECIMAL(10, 2),
    target_date DATE,
    category VARCHAR(50),  -- emergency_fund, purchase, investment
    status VARCHAR(20),  -- active, completed, cancelled
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE advice_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    tip_id INTEGER,
    displayed_at TIMESTAMP,
    was_helpful BOOLEAN,
    feedback_text TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (tip_id) REFERENCES financial_tip(id)
);

CREATE TABLE user_insights (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    insight_type VARCHAR(50),  -- savings_streak, milestone, warning
    insight_data JSON,
    generated_at TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

#### Advice Engine Components

**1. Behavioral Analyzer**
```python
class BehavioralAnalyzer:
    def analyze_user_patterns(self, user_id):
        """Analyze user's savings patterns"""
        contributions = get_user_contributions(user_id, days=90)
        
        return {
            'avg_monthly_savings': calculate_avg(contributions),
            'consistency_score': calculate_consistency(contributions),
            'savings_trend': calculate_trend(contributions),
            'best_saving_day': find_peak_day(contributions),
            'risk_factors': identify_risks(contributions)
        }
```

**2. Goal Progress Tracker**
```python
class GoalTracker:
    def calculate_goal_progress(self, user_id, goal_id):
        """Calculate progress towards financial goal"""
        goal = FinancialGoal.query.get(goal_id)
        total_saved = get_total_savings(user_id)
        
        return {
            'progress_percentage': (total_saved / goal.target_amount) * 100,
            'on_track': is_on_track(goal, total_saved),
            'estimated_completion': estimate_completion_date(goal, total_saved),
            'recommended_actions': generate_recommendations(goal, total_saved)
        }
```

**3. Advice Recommender**
```python
class AdviceRecommender:
    def get_personalized_advice(self, user_id):
        """Generate personalized advice based on user context"""
        insights = BehavioralAnalyzer().analyze_user_patterns(user_id)
        goals = FinancialGoal.query.filter_by(user_id=user_id, status='active').all()
        
        advice_pool = []
        
        # Add goal-specific advice
        for goal in goals:
            progress = GoalTracker().calculate_goal_progress(user_id, goal.id)
            advice_pool.extend(generate_goal_advice(goal, progress))
        
        # Add behavior-based advice
        if insights['consistency_score'] < 0.5:
            advice_pool.append(get_consistency_tips())
        
        if insights['savings_trend'] == 'declining':
            advice_pool.append(get_motivation_boost())
        
        # Filter out recently shown advice
        recent_advice = get_recent_advice_history(user_id, days=7)
        filtered_advice = [a for a in advice_pool if a.id not in recent_advice]
        
        return prioritize_and_select(filtered_advice, limit=3)
```

#### UI Components
- **Advice Dashboard Widget**: Display 3 personalized tips
- **Goal Progress Cards**: Visual progress bars with milestones
- **Insight Notifications**: Pop-up alerts for important insights
- **Feedback Mechanism**: Thumbs up/down for each tip

#### Implementation Phases
1. **Phase 1**: Add goal creation and tracking
2. **Phase 2**: Implement behavioral analyzer
3. **Phase 3**: Build advice recommender
4. **Phase 4**: Add feedback loop and machine learning

---

## Feature 2: Multi-Currency Support

### Current State
- Single currency field in Group model
- USD used as base for all conversions
- Static exchange rates in `utils.py`

### Beta Enhancement
Full multi-currency support with real-time exchange rates, per-member currency preferences, and automatic conversions.

### Architecture

#### Database Schema Changes
```sql
ALTER TABLE "user" ADD COLUMN preferred_currency VARCHAR(3) DEFAULT 'USD';
ALTER TABLE "group" ADD COLUMN base_currency VARCHAR(3) DEFAULT 'USD';

CREATE TABLE exchange_rates (
    id INTEGER PRIMARY KEY,
    from_currency VARCHAR(3),
    to_currency VARCHAR(3),
    rate DECIMAL(10, 6),
    updated_at TIMESTAMP,
    source VARCHAR(50),  -- 'api', 'manual', 'fallback'
    UNIQUE(from_currency, to_currency)
);

CREATE TABLE multi_currency_transactions (
    transaction_id INTEGER PRIMARY KEY,
    original_amount DECIMAL(10, 2),
    original_currency VARCHAR(3),
    converted_amount DECIMAL(10, 2),
    exchange_rate DECIMAL(10, 6),
    conversion_date TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transaction(id)
);
```

#### Exchange Rate Service

**1. Rate Fetcher**
```python
class ExchangeRateService:
    def __init__(self):
        self.api_key = os.environ.get('EXCHANGE_RATE_API_KEY')
        self.base_url = 'https://api.exchangerate.host/latest'
    
    def fetch_latest_rates(self, base_currency='USD'):
        """Fetch latest rates from API"""
        try:
            response = requests.get(
                self.base_url,
                params={'base': base_currency},
                timeout=5
            )
            data = response.json()
            
            self.update_database(data['rates'], base_currency)
            return data['rates']
        except Exception as e:
            logger.error(f"Failed to fetch rates: {e}")
            return self.get_cached_rates(base_currency)
    
    def update_database(self, rates, base_currency):
        """Update exchange rates in database"""
        for currency, rate in rates.items():
            ExchangeRate.query.filter_by(
                from_currency=base_currency,
                to_currency=currency
            ).update({
                'rate': rate,
                'updated_at': datetime.utcnow(),
                'source': 'api'
            })
        db.session.commit()
    
    def get_cached_rates(self, base_currency):
        """Get cached rates as fallback"""
        rates = ExchangeRate.query.filter_by(
            from_currency=base_currency
        ).all()
        return {r.to_currency: r.rate for r in rates}
```

**2. Multi-Currency Converter**
```python
class CurrencyConverter:
    def convert_transaction(self, amount, from_currency, to_currency):
        """Convert amount with audit trail"""
        if from_currency == to_currency:
            return amount, 1.0
        
        rate = self.get_exchange_rate(from_currency, to_currency)
        converted = round(amount * rate, 2)
        
        return converted, rate
    
    def get_exchange_rate(self, from_currency, to_currency):
        """Get exchange rate with caching"""
        rate_record = ExchangeRate.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency
        ).first()
        
        if not rate_record or self.is_stale(rate_record):
            ExchangeRateService().fetch_latest_rates(from_currency)
            rate_record = ExchangeRate.query.filter_by(
                from_currency=from_currency,
                to_currency=to_currency
            ).first()
        
        return rate_record.rate if rate_record else 1.0
    
    def is_stale(self, rate_record):
        """Check if rate is older than 24 hours"""
        return (datetime.utcnow() - rate_record.updated_at).days > 0
```

#### UI Components
- **Currency Selector**: Dropdown in user profile
- **Transaction Currency Display**: Show original + converted amounts
- **Group Currency Settings**: Set base currency on creation
- **Exchange Rate Dashboard**: View current rates and history
- **Conversion Calculator**: Standalone currency converter tool

#### Implementation Considerations
- **API Selection**: Use free tier of exchangerate.host or fixer.io
- **Caching Strategy**: Cache rates for 24 hours, update daily
- **Fallback Mechanism**: Use last known rates if API fails
- **Historical Tracking**: Store conversion rate at transaction time
- **Reporting**: All reports use group's base currency

---

## Feature 3: Gamified Rewards Enhancement

### Current State
- 6 basic badges based on contribution amount and group count
- Badges awarded automatically after transactions
- Simple badge display on dashboard

### Beta Enhancement
Comprehensive gamification with levels, streaks, challenges, leaderboards, and social features.

### Architecture

#### Database Schema Changes
```sql
CREATE TABLE user_levels (
    user_id INTEGER PRIMARY KEY,
    current_level INTEGER DEFAULT 1,
    total_xp INTEGER DEFAULT 0,
    xp_to_next_level INTEGER,
    level_name VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE challenges (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200),
    description TEXT,
    challenge_type VARCHAR(50),  -- daily, weekly, monthly, special
    criteria JSON,  -- {type: 'contribute_x_times', value: 5}
    xp_reward INTEGER,
    badge_reward INTEGER,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE user_challenges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    challenge_id INTEGER,
    progress INTEGER DEFAULT 0,
    status VARCHAR(20),  -- active, completed, expired
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id)
);

CREATE TABLE savings_streaks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_contribution_date DATE,
    streak_type VARCHAR(20),  -- daily, weekly, monthly
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE leaderboard_entries (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    category VARCHAR(50),  -- total_saved, contributions, streak, level
    rank INTEGER,
    score DECIMAL(10, 2),
    period VARCHAR(20),  -- weekly, monthly, all_time
    calculated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

#### Gamification Engine

**1. XP System**
```python
class ExperienceSystem:
    XP_LEVELS = {
        1: 0, 2: 100, 3: 250, 4: 500, 5: 1000,
        6: 2000, 7: 4000, 8: 8000, 9: 16000, 10: 32000
    }
    
    LEVEL_NAMES = {
        1: 'Beginner Saver', 2: 'Penny Pincher', 3: 'Consistent Saver',
        4: 'Smart Saver', 5: 'Savings Pro', 6: 'Finance Expert',
        7: 'Wealth Builder', 8: 'Financial Guru', 9: 'Savings Master',
        10: 'Legendary Saver'
    }
    
    def award_xp(self, user_id, xp_amount, reason):
        """Award XP and handle level ups"""
        user_level = UserLevel.query.get(user_id)
        user_level.total_xp += xp_amount
        
        new_level = self.calculate_level(user_level.total_xp)
        leveled_up = new_level > user_level.current_level
        
        if leveled_up:
            user_level.current_level = new_level
            user_level.level_name = self.LEVEL_NAMES[new_level]
            self.trigger_level_up_rewards(user_id, new_level)
        
        user_level.xp_to_next_level = self.XP_LEVELS[new_level + 1] - user_level.total_xp
        db.session.commit()
        
        return {
            'leveled_up': leveled_up,
            'new_level': new_level,
            'xp_earned': xp_amount
        }
```

**2. Streak Tracker**
```python
class StreakTracker:
    def update_streak(self, user_id, contribution_date):
        """Update user's savings streak"""
        streak = SavingsStreak.query.filter_by(user_id=user_id).first()
        
        if not streak:
            streak = SavingsStreak(user_id=user_id, current_streak=1)
            db.session.add(streak)
        else:
            days_since_last = (contribution_date - streak.last_contribution_date).days
            
            if days_since_last == 1:
                # Consecutive day
                streak.current_streak += 1
                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak
            elif days_since_last > 1:
                # Streak broken
                streak.current_streak = 1
        
        streak.last_contribution_date = contribution_date
        db.session.commit()
        
        # Award XP for milestones
        if streak.current_streak in [7, 30, 100, 365]:
            ExperienceSystem().award_xp(user_id, streak.current_streak * 10, 'streak_milestone')
        
        return streak
```

**3. Challenge System**
```python
class ChallengeManager:
    def check_challenge_progress(self, user_id):
        """Check and update all active challenges for user"""
        active_challenges = UserChallenge.query.filter_by(
            user_id=user_id,
            status='active'
        ).all()
        
        completed = []
        for user_challenge in active_challenges:
            challenge = user_challenge.challenge
            progress = self.calculate_progress(user_id, challenge)
            user_challenge.progress = progress
            
            if progress >= 100:
                user_challenge.status = 'completed'
                user_challenge.completed_at = datetime.utcnow()
                self.award_challenge_rewards(user_id, challenge)
                completed.append(challenge)
        
        db.session.commit()
        return completed
    
    def generate_daily_challenges(self):
        """Generate new daily challenges"""
        challenges = [
            {
                'name': 'Daily Contributor',
                'description': 'Make a contribution today',
                'criteria': {'type': 'contribute', 'count': 1},
                'xp_reward': 50
            },
            {
                'name': 'Social Saver',
                'description': 'Join a new savings group',
                'criteria': {'type': 'join_group', 'count': 1},
                'xp_reward': 100
            }
        ]
        
        for challenge_data in challenges:
            challenge = Challenge(**challenge_data, challenge_type='daily')
            db.session.add(challenge)
        
        db.session.commit()
```

**4. Leaderboard System**
```python
class LeaderboardManager:
    def update_leaderboards(self, period='weekly'):
        """Update all leaderboards for given period"""
        categories = ['total_saved', 'contributions', 'streak', 'level']
        
        for category in categories:
            rankings = self.calculate_rankings(category, period)
            
            for rank, (user_id, score) in enumerate(rankings, 1):
                entry = LeaderboardEntry(
                    user_id=user_id,
                    category=category,
                    rank=rank,
                    score=score,
                    period=period,
                    calculated_at=datetime.utcnow()
                )
                db.session.add(entry)
        
        db.session.commit()
    
    def get_user_rank(self, user_id, category, period='all_time'):
        """Get user's rank in specific category"""
        entry = LeaderboardEntry.query.filter_by(
            user_id=user_id,
            category=category,
            period=period
        ).order_by(LeaderboardEntry.calculated_at.desc()).first()
        
        return entry.rank if entry else None
```

#### UI Components
- **Level Progress Bar**: Display XP and level prominently
- **Streak Calendar**: Visual calendar showing contribution days
- **Challenge Cards**: Active challenges with progress bars
- **Leaderboard Page**: Top savers across categories
- **Achievement Showcase**: Earned badges with rarity indicators
- **Social Feed**: See friends' achievements and milestones

#### Reward Mechanics
- **Contribution XP**: Base amount + bonuses for consistency
- **Level Up Rewards**: Unlock exclusive badges, titles, features
- **Challenge Completion**: XP + special badges + potential prizes
- **Streak Bonuses**: XP multipliers for long streaks
- **Leaderboard Rewards**: Weekly/monthly prizes for top ranks

---

## Implementation Priority

1. **Multi-Currency Support** (Highest)
   - Most requested feature
   - Critical for international users
   - Foundation for other features

2. **Dynamic Financial Advice** (High)
   - High user engagement potential
   - Differentiator from competitors
   - Drives user retention

3. **Gamified Rewards** (Medium)
   - Nice-to-have enhancement
   - Increases engagement
   - Requires significant UI work

## Technical Dependencies

### APIs & Services
- Exchange Rate API (multi-currency)
- Scheduled tasks (Celery/APScheduler for daily challenges)
- Caching layer (Redis for leaderboards)
- Analytics platform (track engagement)

### Infrastructure
- Background job processing
- Increased database storage
- CDN for badge images
- Email/push notification service

## Testing Strategy
- Unit tests for all calculation logic
- Integration tests for multi-step flows
- Load testing for leaderboards
- A/B testing for gamification features
- User acceptance testing with beta group

## Rollout Plan
1. **Alpha**: Internal testing (2 weeks)
2. **Beta**: Limited user group (1 month)
3. **Gradual Rollout**: 25% → 50% → 100% (2 weeks)
4. **Monitoring**: Track metrics and gather feedback
5. **Iteration**: Refine based on data
