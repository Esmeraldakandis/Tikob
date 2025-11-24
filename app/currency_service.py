from models import db, ExchangeRate, UserCurrency
from datetime import datetime, timedelta
import os

EXCHANGE_RATE_API_KEY = os.environ.get('EXCHANGE_RATE_API_KEY')
SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'HTG', 'NGN', 'KES', 'GHS']

def fetch_exchange_rates():
    """Fetch latest exchange rates from API (mock implementation)"""
    if not EXCHANGE_RATE_API_KEY:
        print("WARNING: EXCHANGE_RATE_API_KEY not set. Using mock rates.")
        mock_rates = {
            'EUR': 0.92,
            'GBP': 0.79,
            'HTG': 131.50,
            'NGN': 1580.00,
            'KES': 154.00,
            'GHS': 15.80
        }
        
        for currency, rate in mock_rates.items():
            existing_rate = ExchangeRate.query.filter_by(
                base_currency='USD',
                target_currency=currency
            ).first()
            
            if existing_rate:
                existing_rate.rate = rate
                existing_rate.last_updated = datetime.utcnow()
            else:
                new_rate = ExchangeRate(
                    base_currency='USD',
                    target_currency=currency,
                    rate=rate
                )
                db.session.add(new_rate)
        
        db.session.commit()
        return True
    
    return False

def convert_amount(amount, from_currency='USD', to_currency='USD'):
    """Convert amount from one currency to another"""
    if from_currency == to_currency:
        return amount
    
    if from_currency == 'USD':
        rate = ExchangeRate.query.filter_by(
            base_currency='USD',
            target_currency=to_currency
        ).first()
        
        if rate:
            if (datetime.utcnow() - rate.last_updated).days > 1:
                fetch_exchange_rates()
                rate = ExchangeRate.query.filter_by(
                    base_currency='USD',
                    target_currency=to_currency
                ).first()
            
            return amount * rate.rate
    
    elif to_currency == 'USD':
        rate = ExchangeRate.query.filter_by(
            base_currency='USD',
            target_currency=from_currency
        ).first()
        
        if rate:
            return amount / rate.rate
    
    else:
        usd_amount = convert_amount(amount, from_currency, 'USD')
        return convert_amount(usd_amount, 'USD', to_currency)
    
    return amount

def get_user_currency(user_id):
    """Get user's preferred currency"""
    user_currency = UserCurrency.query.filter_by(user_id=user_id).first()
    
    if user_currency:
        return user_currency.preferred_currency
    
    return 'USD'

def set_user_currency(user_id, currency):
    """Set user's preferred currency"""
    if currency not in SUPPORTED_CURRENCIES:
        return False
    
    user_currency = UserCurrency.query.filter_by(user_id=user_id).first()
    
    if user_currency:
        user_currency.preferred_currency = currency
    else:
        user_currency = UserCurrency(user_id=user_id, preferred_currency=currency)
        db.session.add(user_currency)
    
    db.session.commit()
    return True

def format_currency(amount, currency='USD'):
    """Format amount with currency symbol"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'HTG': 'G',
        'NGN': '₦',
        'KES': 'KSh',
        'GHS': 'GH₵'
    }
    
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:.2f}"
