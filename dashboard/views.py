from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from decimal import Decimal
from supabase_service import get_service_client
import logging

logger = logging.getLogger(__name__)


def dashboard_view(request):
    """Display dashboard for authenticated users with real data from database.
    
    Shows:
    - Daily allowance and spending summary
    - Budget usage by category
    - Active savings goals
    - Recent expenses
    - Budget alerts
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to access dashboard")
        return redirect('login:login_page')
    
    username = request.session.get('username', 'User')
    email = request.session.get('email', '')
    
    try:
        # Import models and constants
        from expenses.views import CATEGORIES
        from savings_goals.models import SavingsGoal
        
        # Get Supabase client
        supabase = get_service_client()
        
        # Get today's date
        today = timezone.now().date()
        today_str = today.isoformat()
        
        # Calculate date ranges
        start_of_month = today.replace(day=1).isoformat()
        start_of_week = (today - timedelta(days=today.weekday())).isoformat()
        
        # ===== DAILY ALLOWANCE SECTION =====
        try:
            # Get today's expenses from Supabase
            today_result = supabase.table('expenses')\
                .select('amount')\
                .eq('user_id', user_id)\
                .eq('date', today_str)\
                .execute()
            
            today_expenses = sum(Decimal(str(e['amount'])) for e in today_result.data) if today_result.data else Decimal('0.00')
            
            # Get this week's expenses
            week_result = supabase.table('expenses')\
                .select('amount')\
                .eq('user_id', user_id)\
                .gte('date', start_of_week)\
                .execute()
            
            week_expenses = sum(Decimal(str(e['amount'])) for e in week_result.data) if week_result.data else Decimal('0.00')
            
            # Get this month's expenses
            month_result = supabase.table('expenses')\
                .select('amount')\
                .eq('user_id', user_id)\
                .gte('date', start_of_month)\
                .execute()
            
            month_expenses = sum(Decimal(str(e['amount'])) for e in month_result.data) if month_result.data else Decimal('0.00')
            
            # Placeholder daily allowance (you can add a user preferences table later)
            daily_allowance = Decimal('500.00')
            remaining_today = daily_allowance - today_expenses
            
            logger.info(f"Dashboard: user {user_id} - Today: ₱{today_expenses}, Week: ₱{week_expenses}, Month: ₱{month_expenses}")
            
        except Exception as e:
            logger.error(f"Error calculating expenses for user {user_id}: {e}", exc_info=True)
            today_expenses = week_expenses = month_expenses = Decimal('0.00')
            daily_allowance = Decimal('500.00')
            remaining_today = daily_allowance
        
        # ===== BUDGET USAGE BY CATEGORY =====
        try:
            category_spending = []
            
            # Get all month expenses from Supabase
            month_expenses_data = supabase.table('expenses')\
                .select('category, amount')\
                .eq('user_id', user_id)\
                .gte('date', start_of_month)\
                .execute()
            
            # Calculate spending per category
            category_totals = {}
            if month_expenses_data.data:
                for expense in month_expenses_data.data:
                    cat = expense.get('category', 'Other')
                    amount = Decimal(str(expense.get('amount', 0)))
                    category_totals[cat] = category_totals.get(cat, Decimal('0.00')) + amount
            
            # Get budget alerts from Supabase
            budget_alerts_data = supabase.table('budget_alerts')\
                .select('category, amount_limit')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            
            budget_limits = {}
            if budget_alerts_data.data:
                for alert in budget_alerts_data.data:
                    budget_limits[alert['category']] = Decimal(str(alert['amount_limit']))
            
            # Build category spending list
            for category in CATEGORIES[:5]:  # Top 5 categories
                spent = category_totals.get(category, Decimal('0.00'))
                budget_limit = budget_limits.get(category, Decimal('1000.00'))
                percentage = min((spent / budget_limit * 100) if budget_limit > 0 else 0, 100)
                
                category_spending.append({
                    'name': category,
                    'spent': spent,
                    'budget': budget_limit,
                    'percentage': round(float(percentage), 1)
                })
            
            # Sort by spending amount
            category_spending.sort(key=lambda x: x['spent'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error calculating category spending for user {user_id}: {e}", exc_info=True)
            category_spending = []
        
        # ===== SAVINGS GOALS =====
        try:
            active_goals = SavingsGoal.objects.filter(
                user_id=user_id,
                status='active'
            ).order_by('-created_at')[:3]  # Top 3 active goals
            
            total_savings_target = SavingsGoal.objects.filter(
                user_id=user_id,
                status='active'
            ).aggregate(total=Sum('target_amount'))['total'] or Decimal('0.00')
            
            total_savings_current = SavingsGoal.objects.filter(
                user_id=user_id,
                status='active'
            ).aggregate(total=Sum('current_amount'))['total'] or Decimal('0.00')
            
        except Exception as e:
            logger.error(f"Error fetching savings goals for user {user_id}: {e}", exc_info=True)
            active_goals = []
            total_savings_target = Decimal('0.00')
            total_savings_current = Decimal('0.00')
        
        # ===== RECENT EXPENSES =====
        try:
            recent_result = supabase.table('expenses')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('date', desc=True)\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute()
            
            recent_expenses = recent_result.data if recent_result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching recent expenses for user {user_id}: {e}", exc_info=True)
            recent_expenses = []
        
        # ===== BUDGET ALERTS =====
        try:
            triggered_alerts = []
            
            # Get active budget alerts from Supabase
            alerts_result = supabase.table('budget_alerts')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            
            if alerts_result.data:
                for alert in alerts_result.data:
                    category = alert['category']
                    spent = category_totals.get(category, Decimal('0.00'))
                    limit = Decimal(str(alert['amount_limit']))
                    threshold_percent = alert['threshold_percent']
                    threshold_amount = limit * (Decimal(threshold_percent) / 100)
                    
                    if spent >= threshold_amount:
                        percentage = min((spent / limit * 100) if limit > 0 else 0, 100)
                        triggered_alerts.append({
                            'category': category,
                            'spent': spent,
                            'limit': limit,
                            'percentage': round(float(percentage), 1),
                            'threshold': threshold_percent
                        })
            
        except Exception as e:
            logger.error(f"Error checking budget alerts for user {user_id}: {e}", exc_info=True)
            triggered_alerts = []
        
        # ===== NOTIFICATIONS (REMINDERS) =====
        try:
            notifications_result = supabase.table('reminders') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('is_completed', False) \
                .order('due_at', desc=False) \
                .limit(10) \
                .execute()

            notifications = notifications_result.data if notifications_result.data else []
            # Parse due_at strings to datetime objects for template rendering
            for notification in notifications:
                if notification.get('due_at'):
                    parsed_dt = parse_datetime(notification['due_at'])
                    if parsed_dt:
                        notification['due_at'] = parsed_dt

        except Exception as e:
            logger.error(f"Error fetching notifications for user {user_id}: {e}", exc_info=True)
            notifications = []

        context = {
            'username': username,
            'email': email,
            'user_id': user_id,
            # Daily allowance
            'daily_allowance': daily_allowance,
            'today_expenses': today_expenses,
            'remaining_today': remaining_today,
            'week_expenses': week_expenses,
            'month_expenses': month_expenses,
            # Budget usage
            'category_spending': category_spending,
            # Savings goals
            'active_goals': active_goals,
            'total_savings_target': total_savings_target,
            'total_savings_current': total_savings_current,
            # Recent activity
            'recent_expenses': recent_expenses,
            # Alerts
            'triggered_alerts': triggered_alerts,
            # Notifications
            'notifications': notifications,
        }
        
        logger.info(f"Dashboard loaded successfully for user {user_id}")
        return render(request, 'dashboard/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Unexpected error loading dashboard for user {user_id}: {e}", exc_info=True)
        # Return minimal context on error
        context = {
            'username': username,
            'email': email,
            'user_id': user_id,
        }
        return render(request, 'dashboard/dashboard.html', context)
