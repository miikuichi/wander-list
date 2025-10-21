from django.shortcuts import render, redirect
from supabase_service import get_service_client
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def dashboard_view(request):
    """Display dashboard for authenticated users with budget alerts.
    
    Authentication is handled by the SupabaseAuthMiddleware.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    username = request.session.get('username', 'User')
    email = request.session.get('email', '')
    
    # Calculate triggered budget alerts
    triggered_alerts = []
    
    try:
        supabase = get_service_client()
        
        # 1. Fetch active budget alerts with category info
        alerts_response = supabase.table('budget_alerts_budgetalert')\
            .select('*, budget_alerts_category(*)')\
            .eq('user_id', user_id)\
            .eq('active', True)\
            .execute()
        
        budget_alerts = alerts_response.data if alerts_response.data else []
        
        # 2. Get current month's date range
        today = datetime.now()
        first_day_of_month = today.replace(day=1).date()
        
        # 3. Fetch all expenses for current month
        expenses_response = supabase.table('expenses')\
            .select('category, amount')\
            .eq('user_id', user_id)\
            .gte('date', str(first_day_of_month))\
            .execute()
        
        expenses = expenses_response.data if expenses_response.data else []
        
        # 4. Calculate spending by category
        spending_by_category = {}
        for expense in expenses:
            category = expense['category']
            amount = Decimal(str(expense['amount']))
            spending_by_category[category] = spending_by_category.get(category, Decimal('0')) + amount
        
        # 5. Check each budget alert against actual spending
        for alert in budget_alerts:
            category_name = alert['budget_alerts_category']['name']
            amount_limit = Decimal(str(alert['amount_limit']))
            threshold_percent = alert['threshold_percent']
            notify_dashboard = alert['notify_dashboard']
            
            # Get spending for this category
            spent = spending_by_category.get(category_name, Decimal('0'))
            
            # Calculate percentage spent
            if amount_limit > 0:
                percent_spent = (spent / amount_limit) * 100
            else:
                percent_spent = 0
            
            # Check if threshold is exceeded and dashboard notifications are enabled
            if notify_dashboard and percent_spent >= threshold_percent:
                triggered_alerts.append({
                    'category': category_name,
                    'spent': float(spent),
                    'limit': float(amount_limit),
                    'percent_spent': round(percent_spent, 1),
                    'threshold': threshold_percent,
                    'severity': 'danger' if percent_spent >= 100 else 'warning'
                })
        
        logger.info(f"Dashboard: Found {len(triggered_alerts)} triggered alerts for user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Failed to calculate budget alerts: {e}", exc_info=True)
        # Don't block dashboard if alerts fail
    
    context = {
        'username': username,
        'email': email,
        'user_id': user_id,
        'triggered_alerts': triggered_alerts,
    }
    return render(request, 'dashboard/dashboard.html', context)
