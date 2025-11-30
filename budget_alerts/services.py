"""
Budget Analysis Services
Provides advanced budget tracking, predictions, and health score calculations.
"""
from decimal import Decimal
from datetime import datetime, timedelta, date
from collections import defaultdict
from supabase_service import get_service_client
import logging

logger = logging.getLogger(__name__)


def get_budget_vs_actual(user_id, start_date=None, end_date=None):
    """
    Compare budgeted amounts vs actual spending per category.
    
    Returns:
        dict: {
            'category_name': {
                'budget': Decimal,
                'actual': Decimal,
                'variance': Decimal,
                'variance_percent': float,
                'status': 'under'|'over'|'on_target'
            }
        }
    """
    supabase = get_service_client()
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    # Get all budget alerts for user
    alerts_response = supabase.table('budget_alerts_budgetalert')\
        .select('*, category:category_id(*)')\
        .eq('user_id', user_id)\
        .eq('active', True)\
        .execute()
    
    # Get actual spending for the period
    expenses_response = supabase.table('expenses')\
        .select('category, amount')\
        .eq('user_id', user_id)\
        .gte('date', start_date.isoformat())\
        .lte('date', end_date.isoformat())\
        .execute()
    
    # Aggregate expenses by category
    actual_spending = defaultdict(Decimal)
    for expense in expenses_response.data:
        category = expense.get('category', 'Other')
        amount = Decimal(str(expense.get('amount', 0)))
        actual_spending[category] += amount
    
    # Build comparison
    comparison = {}
    for alert in alerts_response.data:
        category_name = alert['category']['name']
        budget = Decimal(str(alert['amount_limit']))
        actual = actual_spending.get(category_name, Decimal('0.00'))
        variance = budget - actual
        variance_percent = float((variance / budget * 100)) if budget > 0 else 0.0
        
        if actual < budget * Decimal('0.95'):
            status = 'under'
        elif actual > budget:
            status = 'over'
        else:
            status = 'on_target'
        
        comparison[category_name] = {
            'budget': budget,
            'actual': actual,
            'variance': variance,
            'variance_percent': variance_percent,
            'status': status,
            'usage_percent': float((actual / budget * 100)) if budget > 0 else 0.0
        }
    
    return comparison


def calculate_category_health_score(user_id, category, budget_limit):
    """
    Calculate health score for a category (0-100).
    
    Score factors:
    - Current spending percentage (0-100%)
    - Spending trend (increasing/decreasing)
    - Historical adherence
    
    Returns:
        dict: {
            'score': int (0-100),
            'level': 'excellent'|'good'|'warning'|'critical',
            'color': '#hex',
            'message': str
        }
    """
    supabase = get_service_client()
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # Get current month spending
    expenses_response = supabase.table('expenses')\
        .select('amount')\
        .eq('user_id', user_id)\
        .eq('category', category)\
        .gte('date', start_of_month.isoformat())\
        .lte('date', today.isoformat())\
        .execute()
    
    current_spending = sum(Decimal(str(e['amount'])) for e in expenses_response.data)
    budget = Decimal(str(budget_limit))
    usage_percent = float((current_spending / budget * 100)) if budget > 0 else 0.0
    
    # Calculate score (inverse of usage percentage with adjustments)
    if usage_percent <= 70:
        score = 100
        level = 'excellent'
        color = '#28a745'  # Green
        message = 'Well within budget! Excellent spending control.'
    elif usage_percent <= 85:
        score = 85
        level = 'good'
        color = '#34c54a'  # PisoHeroes green
        message = 'Good budget management. Keep it up!'
    elif usage_percent <= 95:
        score = 70
        level = 'warning'
        color = '#ffc107'  # Yellow
        message = 'Approaching budget limit. Monitor spending closely.'
    elif usage_percent <= 100:
        score = 50
        level = 'warning'
        color = '#fd7e14'  # Orange
        message = 'Near budget limit! Be cautious with spending.'
    else:
        score = max(0, 100 - int(usage_percent))
        level = 'critical'
        color = '#dc3545'  # Red
        message = f'Over budget by {usage_percent - 100:.1f}%! Immediate action needed.'
    
    return {
        'score': score,
        'level': level,
        'color': color,
        'message': message,
        'usage_percent': usage_percent,
        'current_spending': current_spending,
        'budget': budget
    }


def predict_budget_breach(user_id, category, budget_limit, days_remaining=None):
    """
    Predict if budget will be breached based on current spending trend.
    
    Uses linear regression on last 7-14 days to predict end-of-month spending.
    
    Returns:
        dict: {
            'will_breach': bool,
            'predicted_spending': Decimal,
            'predicted_date': date or None,
            'daily_average': Decimal,
            'recommended_daily_limit': Decimal,
            'confidence': 'high'|'medium'|'low'
        }
    """
    supabase = get_service_client()
    today = date.today()
    start_of_month = today.replace(day=1)
    
    if days_remaining is None:
        from calendar import monthrange
        days_in_month = monthrange(today.year, today.month)[1]
        days_remaining = days_in_month - today.day
    
    # Get expenses for current month
    expenses_response = supabase.table('expenses')\
        .select('date, amount')\
        .eq('user_id', user_id)\
        .eq('category', category)\
        .gte('date', start_of_month.isoformat())\
        .lte('date', today.isoformat())\
        .execute()
    
    if not expenses_response.data:
        return {
            'will_breach': False,
            'predicted_spending': Decimal('0.00'),
            'predicted_date': None,
            'daily_average': Decimal('0.00'),
            'recommended_daily_limit': Decimal('0.00'),
            'confidence': 'low',
            'message': 'No spending data for predictions.'
        }
    
    # Calculate daily spending
    daily_spending = defaultdict(Decimal)
    for expense in expenses_response.data:
        expense_date = datetime.fromisoformat(expense['date']).date()
        daily_spending[expense_date] += Decimal(str(expense['amount']))
    
    # Calculate average daily spending
    days_with_data = len(daily_spending)
    total_spending = sum(daily_spending.values())
    daily_average = total_spending / days_with_data if days_with_data > 0 else Decimal('0.00')
    
    # Predict end of month spending
    predicted_spending = total_spending + (daily_average * days_remaining)
    budget = Decimal(str(budget_limit))
    
    will_breach = predicted_spending > budget
    
    # Calculate when breach will occur if trend continues
    predicted_date = None
    if will_breach and daily_average > 0:
        remaining_budget = budget - total_spending
        days_until_breach = remaining_budget / daily_average
        if days_until_breach > 0:
            predicted_date = today + timedelta(days=int(days_until_breach))
    
    # Calculate recommended daily limit to stay within budget
    if days_remaining > 0:
        remaining_budget = budget - total_spending
        recommended_daily_limit = remaining_budget / days_remaining
    else:
        recommended_daily_limit = Decimal('0.00')
    
    # Confidence based on data points
    if days_with_data >= 7:
        confidence = 'high'
    elif days_with_data >= 3:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    message = ''
    if will_breach:
        overage = predicted_spending - budget
        message = f'At current rate, you will exceed budget by ₱{overage:.2f} by month end.'
    else:
        message = 'On track to stay within budget if current trend continues.'
    
    return {
        'will_breach': will_breach,
        'predicted_spending': predicted_spending,
        'predicted_date': predicted_date,
        'daily_average': daily_average,
        'recommended_daily_limit': recommended_daily_limit,
        'confidence': confidence,
        'message': message,
        'days_with_data': days_with_data
    }


def get_budget_trends(user_id, category, months=6):
    """
    Get budget limit trends over time from history.
    
    Returns:
        list: [{
            'month': 'YYYY-MM',
            'budget_limit': Decimal,
            'change_from_previous': Decimal,
            'reason': str
        }]
    """
    supabase = get_service_client()
    
    # Get budget history for category
    history_response = supabase.table('budget_alerts_budgethistory')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('category', category)\
        .order('change_date', desc=True)\
        .limit(months)\
        .execute()
    
    trends = []
    for record in reversed(history_response.data):
        change_date = datetime.fromisoformat(record['change_date'])
        trends.append({
            'month': change_date.strftime('%Y-%m'),
            'budget_limit': Decimal(str(record['amount_limit'])),
            'change_from_previous': Decimal(str(record.get('previous_limit', 0))) if record.get('previous_limit') else None,
            'reason': record.get('change_reason', 'Initial budget')
        })
    
    return trends
