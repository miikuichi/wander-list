from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange
from supabase_service import get_service_client
import logging
from login.decorators import require_authentication
from audit_logs.services import log_update
from login.models import User

logger = logging.getLogger(__name__)


def _days_in_current_month(d: date | None = None) -> int:
    """
    Helper: number of days in the given date's month (or current month if None).
    """
    d = d or date.today()
    return monthrange(d.year, d.month)[1]


@require_authentication
def dashboard_view(request):
    """Display dashboard for authenticated users with real data from database.
    
    Shows:
    - Daily allowance and spending summary
    - Budget usage by category
    - Active savings goals
    - Recent expenses
    - Budget alerts
    """

    if request.session.get('is_admin'):
        return redirect('admin_dashboard')
    
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

        # Lazy import of user_settings service to avoid import-time issues
        try:
            from services.user_settings import get_monthly_allowance
        except Exception:
            # If the import fails, provide a safe stub so the view still runs
            def get_monthly_allowance(supabase_client, uid):
                return None

        # Get today's date
        today = timezone.now().date()
        today_str = today.isoformat()
        
        # Calculate date ranges
        start_of_month = today.replace(day=1).isoformat()
        start_of_week = (today - timedelta(days=today.weekday())).isoformat()

        # Range selector for Budget Usage chart
        budget_range = request.GET.get('budget_range', 'monthly')
        if budget_range not in ['daily', 'weekly', 'monthly']:
            budget_range = 'monthly'
        
        # ===== DAILY ALLOWANCE SECTION (MODIFIED) =====
        # Label: START_DAILY_ALLOWANCE
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
            
            # --- NEW: read user's monthly allowance from Supabase and compute daily ---
            days_this_month = _days_in_current_month()
            monthly_allowance = None
            try:
                monthly_allowance = get_monthly_allowance(supabase, user_id)
            except Exception as e:
                logger.error(f"Failed to read monthly allowance for user {user_id}: {e}", exc_info=True)
                monthly_allowance = None

            if monthly_allowance and monthly_allowance > 0:
                daily_allowance = (monthly_allowance / Decimal(days_this_month))\
                    .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                # fallback to previous default if user hasn't set monthly allowance
                daily_allowance = Decimal('500.00')
                monthly_allowance = None

            remaining_today = daily_allowance - today_expenses
            
            logger.info(
                f"Dashboard: user {user_id} - Today: ₱{today_expenses}, Week: ₱{week_expenses}, "
                f"Month: ₱{month_expenses}, Daily: ₱{daily_allowance} (monthly={monthly_allowance})"
            )
            
        except Exception as e:
            logger.error(f"Error calculating expenses for user {user_id}: {e}", exc_info=True)
            today_expenses = week_expenses = month_expenses = Decimal('0.00')
            daily_allowance = Decimal('500.00')
            remaining_today = daily_allowance
            monthly_allowance = None
            days_this_month = _days_in_current_month()
        # Label: END_DAILY_ALLOWANCE
        
        # ===== BUDGET USAGE BY CATEGORY =====
        try:
            category_spending = []
            
            # Pick date range for the chart based on budget_range
            if budget_range == 'daily':
                range_query = supabase.table('expenses')\
                    .select('category, amount')\
                    .eq('user_id', user_id)\
                    .eq('date', today_str)
            elif budget_range == 'weekly':
                range_query = supabase.table('expenses')\
                    .select('category, amount')\
                    .eq('user_id', user_id)\
                    .gte('date', start_of_week)\
                    .lte('date', today_str)
            else:  # monthly (default)
                range_query = supabase.table('expenses')\
                    .select('category, amount')\
                    .eq('user_id', user_id)\
                    .gte('date', start_of_month)\
                    .lte('date', today_str)

            range_expenses_data = range_query.execute()
            
            # Calculate spending per category for the chart
            category_totals_chart = {}
            if range_expenses_data.data:
                for expense in range_expenses_data.data:
                    cat = expense.get('category', 'Other')
                    amount = Decimal(str(expense.get('amount', 0)))
                    category_totals_chart[cat] = category_totals_chart.get(cat, Decimal('0.00')) + amount
            
            # Get budget alerts from Supabase (for budget limits)
            budget_alerts_data = supabase.table('budget_alerts')\
                .select('category, amount_limit')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            
            budget_limits = {}
            if budget_alerts_data.data:
                for alert in budget_alerts_data.data:
                    budget_limits[alert['category']] = Decimal(str(alert['amount_limit']))
            
            # Build category spending list for the pie chart
            for category in CATEGORIES[:5]:  # Top 5 categories
                spent = category_totals_chart.get(category, Decimal('0.00'))
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
            
            # Month-to-date spending per category for alerts (always monthly)
            month_expenses_for_alerts = supabase.table('expenses')\
                .select('category, amount')\
                .eq('user_id', user_id)\
                .gte('date', start_of_month)\
                .lte('date', today_str)\
                .execute()

            category_totals_month = {}
            if month_expenses_for_alerts.data:
                for exp in month_expenses_for_alerts.data:
                    cat = exp.get('category', 'Other')
                    amount = Decimal(str(exp.get('amount', 0)))
                    category_totals_month[cat] = category_totals_month.get(cat, Decimal('0.00')) + amount
            
            # Get active budget alerts from Supabase
            alerts_result = supabase.table('budget_alerts')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            
            if alerts_result.data:
                # Import notification service and model
                from notifications.services import NotificationService
                from notifications.models import NotificationLog
                
                for alert in alerts_result.data:
                    category = alert['category']
                    spent = category_totals_month.get(category, Decimal('0.00'))
                    limit = Decimal(str(alert['amount_limit']))
                    threshold_percent = alert['threshold_percent']
                    threshold_amount = limit * (Decimal(threshold_percent) / 100)
                    
                    if spent >= threshold_amount:
                        percentage = min((spent / limit * 100) if limit > 0 else 0, 100)
                        
                        # Check if we already sent a notification today for this category
                        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                        existing_notification = NotificationLog.objects.filter(
                            user_id=user_id,
                            category='budget_alert',
                            related_object_type='budget_alert',
                            title__icontains=category,
                            created_at__gte=today_start
                        ).exists()
                        
                        # Only create notification if we haven't sent one today
                        if not existing_notification:
                            try:
                                NotificationService.create_budget_alert_notification(
                                    user_id=user_id,
                                    category=category,
                                    spent=float(spent),
                                    limit=float(limit),
                                    percentage=float(percentage),
                                    threshold=threshold_percent,
                                    user_email=email,
                                )
                                logger.info(f"Created budget alert notification for user {user_id}, category {category}")
                            except Exception as notif_error:
                                logger.error(f"Failed to create budget alert notification: {notif_error}")
            
        except Exception as e:
            logger.error(f"Error checking budget alerts for user {user_id}: {e}", exc_info=True)
        
        # ===== NOTIFICATIONS (REMINDERS) =====
        try:
            notifications_result = supabase.table('reminders') \
                .select('*') \
                .eq('user_id', user_id)\
                .eq('is_completed', False)\
                .order('due_at', desc=False)\
                .limit(10)\
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

        if budget_range == 'daily':
            budget_range_label = 'day'
        elif budget_range == 'weekly':
            budget_range_label = 'week'
        else:
            budget_range_label = 'month'

        context = {
            'username': username,
            'email': email,
            'user_id': user_id,
            # Daily allowance
            'daily_allowance': daily_allowance,
            'monthly_allowance': monthly_allowance,     # <-- NEW: passed to template
            'days_in_month': days_this_month,           # <-- NEW: passed to template
            'today_expenses': today_expenses,
            'remaining_today': remaining_today,
            'week_expenses': week_expenses,
            'month_expenses': month_expenses,
            # Budget usage
            'category_spending': category_spending,
            'budget_range': budget_range,
            'budget_range_label': budget_range_label,
            # Savings goals
            'active_goals': active_goals,
            'total_savings_target': total_savings_target,
            'total_savings_current': total_savings_current,
            # Recent activity
            'recent_expenses': recent_expenses,
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


# ===== NEW VIEW: update_monthly_allowance_view =====
# Label: START_UPDATE_MONTHLY_ALLOWANCE_VIEW
@require_POST
def update_monthly_allowance_view(request):
    """
    POST endpoint that accepts 'monthly_allowance' and upserts it to Supabase.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login:login_page')

    raw = (request.POST.get('monthly_allowance') or '').strip().replace(',', '')
    try:
        value = Decimal(raw)
        if value < 0:
            raise ValueError("negative")
    except Exception:
        logger.warning(f"Invalid monthly_allowance input from user {user_id}: {raw}")
        # Optionally: use Django messages to show invalid input; for now, redirect back
        return redirect('dashboard')  # adjust to your URL name if different

    supabase = get_service_client()
    try:
        # Lazy import setter to avoid import-time issues
        try:
            from services.user_settings import set_monthly_allowance
        except Exception:
            def set_monthly_allowance(supabase_client, uid, val):
                logger.error('set_monthly_allowance not available')
                return None

        set_monthly_allowance(supabase, user_id, value)
    except Exception as e:
        logger.error(f"Failed to save monthly allowance for {user_id}: {e}", exc_info=True)

    return redirect('dashboard')  # adjust to your URL name if different
# Label: END_UPDATE_MONTHLY_ALLOWANCE_VIEW


@require_authentication
def cache_settings_view(request):
    """Display cache management settings page."""
    user_id = request.session.get('user_id')
    username = request.session.get('username', 'User')
    
    context = {
        'username': username,
        'user_id': user_id,
    }
    
    return render(request, 'dashboard/cache_settings.html', context)


def admin_dashboard_view(request):
    """
    Displays a list of all registered users.
    Fetches latest data from Supabase to keep local DB in sync,
    and supports searching by username or email.
    """
    if not request.session.get('is_admin'):
        return redirect('dashboard')

    # Supabase client
    try:
        supabase = get_service_client()
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase = None

    email_to_remote_id = {}

    # 2. SYNC: Fetch all users from Supabase and update local DB
    if supabase:
        try:
            response = supabase.table('login_user').select('*').execute()

            if response.data:
                for remote_user in response.data:
                    email = remote_user['email']
                    email_to_remote_id[email] = remote_user['id']

                    User.objects.update_or_create(
                        email=email,
                        defaults={
                            'username': remote_user.get(
                                'username',
                                email.split('@')[0]
                            ),
                            'is_admin': remote_user.get('is_admin', False),
                            'password': remote_user.get(
                                'password', 'synced_from_supabase'
                            )
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to sync users from Supabase: {e}")

    # 3. SEARCH + STATS
    search_query = request.GET.get('q', '').strip()

    users_qs = User.objects.all()

    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    users_qs = users_qs.order_by('-id')

    # ---- compute daily allowance per user (using Supabase ID) ----
    days_this_month = _days_in_current_month()

    try:
        from services.user_settings import get_monthly_allowance
    except Exception:
        def get_monthly_allowance(*args, **kwargs):
            return None

    from decimal import Decimal, ROUND_HALF_UP

    for u in users_qs:
        monthly = None
        remote_id = email_to_remote_id.get(u.email)

        if supabase and remote_id is not None:
            try:
                monthly = get_monthly_allowance(supabase, remote_id)
            except Exception as e:
                logger.error(f"Failed to get monthly allowance for Supabase user {remote_id}: {e}")

        if monthly and monthly > 0:
            daily = (monthly / Decimal(days_this_month)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            daily = Decimal("500.00")

        u.daily_allowance_value = daily

    # stats for header cards (based on ALL users, not just filtered)
    all_users = User.objects.all()
    total_users = all_users.count()
    total_admins = all_users.filter(is_admin=True).count()
    total_regular = all_users.filter(is_admin=False).count()

    context = {
        'users': users_qs,
        'user_count': total_users,
        'admin_count': total_admins,
        'regular_user_count': total_regular,
        'search_query': search_query,
    }

    return render(request, 'dashboard/admin_dashboard.html', context)
