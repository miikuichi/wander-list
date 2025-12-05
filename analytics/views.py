"""
Analytics views for visual reports and spending insights.

Provides comprehensive data analysis including:
- Daily spending patterns
- Weekly comparisons
- Monthly trends
- Category breakdowns
- Budget adherence metrics
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from login.decorators import require_authentication, require_json_authentication
from supabase_service import get_service_client
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
import calendar
import logging
import csv
from django.http import HttpResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_authentication
def analytics_dashboard(request):
    """
    Main analytics dashboard with date range filters and chart selection.
    """
    user_id = request.session.get('user_id')
    username = request.session.get('username', 'User')
    
    # Get date range from query params (default to current month)
    today = date.today()
    start_date_str = request.GET.get('start_date', today.replace(day=1).isoformat())
    end_date_str = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        start_date = today.replace(day=1)
        end_date = today
    
    # Calculate quick stats
    try:
        supabase = get_service_client()
        
        # Get expenses in date range
        response = supabase.table('expenses')\
            .select('*')\
            .eq('user_id', user_id)\
            .gte('date', start_date.isoformat())\
            .lte('date', end_date.isoformat())\
            .execute()
        
        expenses = response.data if response.data else []
        
        # Calculate summary stats
        total_spent = sum(Decimal(str(exp['amount'])) for exp in expenses)
        expense_count = len(expenses)
        days_in_range = (end_date - start_date).days + 1
        avg_daily = (total_spent / days_in_range) if days_in_range > 0 else Decimal('0')
        
        # Get budget alerts for comparison
        alerts_response = supabase.table('budget_alerts')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('active', True)\
            .execute()
        
        total_budget = sum(Decimal(str(alert['amount_limit'])) 
                          for alert in (alerts_response.data or []))
        
        budget_adherence = 0
        if total_budget > 0:
            budget_adherence = float((1 - (total_spent / total_budget)) * 100)
            budget_adherence = max(0, budget_adherence)  # Can't be negative
        
    except Exception as e:
        logger.error(f"Error loading analytics summary: {e}", exc_info=True)
        total_spent = Decimal('0')
        expense_count = 0
        avg_daily = Decimal('0')
        budget_adherence = 0
    
    context = {
        'username': username,
        'user_id': user_id,
        'start_date': start_date,
        'end_date': end_date,
        'total_spent': total_spent,
        'expense_count': expense_count,
        'avg_daily': avg_daily,
        'budget_adherence': budget_adherence,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@require_json_authentication
def api_daily_spending(request):
    """
    API endpoint for daily spending chart data.
    Returns spending by day within the specified date range.
    """
    user_id = request.session.get('user_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    try:
        supabase = get_service_client()
        response = supabase.table('expenses')\
            .select('date, amount')\
            .eq('user_id', user_id)\
            .gte('date', start_date.isoformat())\
            .lte('date', end_date.isoformat())\
            .order('date')\
            .execute()
        
        # Aggregate by date
        daily_totals = defaultdict(Decimal)
        for exp in (response.data or []):
            daily_totals[exp['date']] += Decimal(str(exp['amount']))
        
        # Fill in missing dates with 0
        current = start_date
        chart_data = []
        while current <= end_date:
            date_str = current.isoformat()
            chart_data.append({
                'date': date_str,
                'amount': float(daily_totals.get(date_str, Decimal('0'))),
                'label': current.strftime('%b %d')
            })
            current += timedelta(days=1)
        
        return JsonResponse({'data': chart_data})
        
    except Exception as e:
        logger.error(f"Error fetching daily spending data: {e}", exc_info=True)
        return JsonResponse({'error': 'Server error'}, status=500)


@require_json_authentication
def api_category_breakdown(request):
    """
    API endpoint for category spending breakdown (pie chart).
    """
    user_id = request.session.get('user_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    try:
        supabase = get_service_client()
        response = supabase.table('expenses')\
            .select('category, amount')\
            .eq('user_id', user_id)\
            .gte('date', start_date.isoformat())\
            .lte('date', end_date.isoformat())\
            .execute()
        
        # Aggregate by category
        category_totals = defaultdict(Decimal)
        for exp in (response.data or []):
            category = exp.get('category', 'Other')
            category_totals[category] += Decimal(str(exp['amount']))
        
        # Convert to chart format
        chart_data = [
            {
                'category': cat,
                'amount': float(amt),
                'percentage': 0  # Will calculate on frontend
            }
            for cat, amt in sorted(
                category_totals.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]
        
        # Calculate percentages
        total = sum(item['amount'] for item in chart_data)
        if total > 0:
            for item in chart_data:
                item['percentage'] = round((item['amount'] / total) * 100, 1)
        
        return JsonResponse({'data': chart_data})
        
    except Exception as e:
        logger.error(f"Error fetching category breakdown: {e}", exc_info=True)
        return JsonResponse({'error': 'Server error'}, status=500)


@require_json_authentication
def api_weekly_comparison(request):
    """
    API endpoint for week-by-week spending comparison.
    """
    user_id = request.session.get('user_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    try:
        supabase = get_service_client()
        response = supabase.table('expenses')\
            .select('date, amount')\
            .eq('user_id', user_id)\
            .gte('date', start_date.isoformat())\
            .lte('date', end_date.isoformat())\
            .execute()
        
        # Group by week
        weekly_totals = defaultdict(Decimal)
        for exp in (response.data or []):
            exp_date = date.fromisoformat(exp['date'])
            # Get week start (Monday)
            week_start = exp_date - timedelta(days=exp_date.weekday())
            week_key = week_start.isoformat()
            weekly_totals[week_key] += Decimal(str(exp['amount']))
        
        # Convert to chart format
        chart_data = []
        for week_start_str in sorted(weekly_totals.keys()):
            week_start = date.fromisoformat(week_start_str)
            week_end = week_start + timedelta(days=6)
            chart_data.append({
                'week_start': week_start_str,
                'week_label': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                'amount': float(weekly_totals[week_start_str])
            })
        
        return JsonResponse({'data': chart_data})
        
    except Exception as e:
        logger.error(f"Error fetching weekly comparison: {e}", exc_info=True)
        return JsonResponse({'error': 'Server error'}, status=500)


@require_json_authentication
def api_monthly_trends(request):
    """
    API endpoint for monthly spending trends (last 6 months).
    Optimized to fetch all data in one query.
    """
    user_id = request.session.get('user_id')
    
    try:
        # Calculate date range for last 6 months
        today = date.today()
        six_months_ago = today.replace(day=1) - timedelta(days=150)
        
        # Fetch all expenses in one query
        supabase = get_service_client()
        response = supabase.table('expenses')\
            .select('date, amount')\
            .eq('user_id', user_id)\
            .gte('date', six_months_ago.isoformat())\
            .lte('date', today.isoformat())\
            .execute()
        
        # Calculate last 6 months info
        months = []
        for i in range(5, -1, -1):  # 6 months including current
            month_date = today.replace(day=1) - timedelta(days=i*30)
            month_date = month_date.replace(day=1)
            last_day = calendar.monthrange(month_date.year, month_date.month)[1]
            months.append({
                'start': month_date,
                'end': month_date.replace(day=last_day),
                'label': month_date.strftime('%B %Y'),
                'key': f"{month_date.year}-{month_date.month:02d}"
            })
        
        # Aggregate expenses by month
        monthly_totals = defaultdict(Decimal)
        for exp in (response.data or []):
            exp_date = date.fromisoformat(exp['date'])
            month_key = f"{exp_date.year}-{exp_date.month:02d}"
            monthly_totals[month_key] += Decimal(str(exp['amount']))
        
        # Build chart data
        chart_data = []
        for month_info in months:
            total = monthly_totals.get(month_info['key'], Decimal('0'))
            chart_data.append({
                'month': month_info['label'],
                'amount': float(total)
            })
        
        return JsonResponse({'data': chart_data})
        
    except Exception as e:
        logger.error(f"Error fetching monthly trends: {e}", exc_info=True)
        return JsonResponse({'error': 'Server error'}, status=500)


@require_json_authentication
def api_hourly_patterns(request):
    """
    API endpoint for hourly spending patterns (what time of day do you spend?).
    """
    user_id = request.session.get('user_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        start_date = date.fromisoformat(start_date_str) if start_date_str else None
        end_date = date.fromisoformat(end_date_str) if end_date_str else None
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    try:
        supabase = get_service_client()
        query = supabase.table('expenses').select('created_at, amount').eq('user_id', user_id)
        
        if start_date:
            query = query.gte('date', start_date.isoformat())
        if end_date:
            query = query.lte('date', end_date.isoformat())
        
        response = query.execute()
        
        # Aggregate by hour
        hourly_totals = defaultdict(lambda: {'count': 0, 'amount': Decimal('0')})
        for exp in (response.data or []):
            if exp.get('created_at'):
                try:
                    created = datetime.fromisoformat(exp['created_at'].replace('Z', '+00:00'))
                    hour = created.hour
                    hourly_totals[hour]['count'] += 1
                    hourly_totals[hour]['amount'] += Decimal(str(exp['amount']))
                except (ValueError, AttributeError):
                    continue
        
        # Convert to chart format
        chart_data = []
        for hour in range(24):
            data = hourly_totals.get(hour, {'count': 0, 'amount': Decimal('0')})
            time_label = f"{hour:02d}:00" if hour < 12 or hour == 24 else f"{hour:02d}:00"
            chart_data.append({
                'hour': hour,
                'time_label': time_label,
                'count': data['count'],
                'amount': float(data['amount'])
            })
        
        return JsonResponse({'data': chart_data})
        
    except Exception as e:
        logger.error(f"Error fetching hourly patterns: {e}", exc_info=True)
        return JsonResponse({'error': 'Server error'}, status=500)
    

@require_GET
@require_authentication
def export_visual_report_csv(request):
    """
    Export the current user's analytics report as CSV including:
    - Raw transactions
    - Daily totals
    - Category breakdown
    - Weekly totals
    - Monthly totals
    - Hourly patterns
    """
    user_id = request.session.get('user_id')

    today = date.today()
    start_date_str = request.GET.get('start_date', today.replace(day=1).isoformat())
    end_date_str = request.GET.get('end_date', today.isoformat())

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        start_date = today.replace(day=1)
        end_date = today

    supabase = get_service_client()

    try:
        response = supabase.table('expenses') \
            .select('date, category, amount, notes, created_at') \
            .eq('user_id', user_id) \
            .gte('date', start_date.isoformat()) \
            .lte('date', end_date.isoformat()) \
            .order('date') \
            .execute()

        expenses = response.data or []

    except Exception as e:
        logger.error(f"CSV export failed: {e}", exc_info=True)
        expenses = []

    filename = f"pisoheroes_user_report_{start_date.isoformat()}_to_{end_date.isoformat()}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # ================= RAW TRANSACTIONS =================
    writer.writerow(['RAW TRANSACTIONS'])
    writer.writerow(['Date', 'Category', 'Amount', 'Notes'])

    for exp in expenses:
        writer.writerow([
            exp.get('date', ''),
            exp.get('category', ''),
            exp.get('amount', ''),
            (exp.get('notes') or '').replace('\n', ' ').replace('\r', ' ')
        ])

    writer.writerow([])

    # ================= DAILY TOTALS =================
    writer.writerow(['DAILY TOTALS'])
    writer.writerow(['Date', 'Total Amount'])

    daily_totals = defaultdict(Decimal)
    for exp in expenses:
        daily_totals[exp['date']] += Decimal(str(exp['amount']))

    for d in sorted(daily_totals):
        writer.writerow([d, float(daily_totals[d])])

    writer.writerow([])

    # ================= CATEGORY BREAKDOWN =================
    writer.writerow(['CATEGORY BREAKDOWN'])
    writer.writerow(['Category', 'Total Amount', 'Percentage'])

    category_totals = defaultdict(Decimal)
    total_all = Decimal('0')

    for exp in expenses:
        category = exp.get('category', 'Other')
        category_totals[category] += Decimal(str(exp['amount']))
        total_all += Decimal(str(exp['amount']))

    for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        percent = (amt / total_all * 100) if total_all else 0
        writer.writerow([cat, float(amt), round(percent, 2)])

    writer.writerow([])

    # ================= WEEKLY TOTALS =================
    writer.writerow(['WEEKLY TOTALS'])
    writer.writerow(['Week Range', 'Total Amount'])

    weekly_totals = defaultdict(Decimal)

    for exp in expenses:
        d = date.fromisoformat(exp['date'])
        week_start = d - timedelta(days=d.weekday())
        week_end = week_start + timedelta(days=6)

        label = f"{week_start:%b %d} - {week_end:%b %d}"
        weekly_totals[label] += Decimal(str(exp['amount']))

    for week, amt in weekly_totals.items():
        writer.writerow([week, float(amt)])

    writer.writerow([])

    # ================= MONTHLY TOTALS =================
    writer.writerow(['MONTHLY TOTALS'])
    writer.writerow(['Month', 'Total Amount'])

    monthly_totals = defaultdict(Decimal)

    for exp in expenses:
        d = date.fromisoformat(exp['date'])
        key = f"{d:%B %Y}"
        monthly_totals[key] += Decimal(str(exp['amount']))

    for month, amt in monthly_totals.items():
        writer.writerow([month, float(amt)])

    writer.writerow([])

    # ================= HOURLY PATTERNS =================
    writer.writerow(['HOURLY PATTERNS'])
    writer.writerow(['Hour', 'Transactions', 'Total Amount'])

    hourly_totals = defaultdict(lambda: {'count': 0, 'amount': Decimal('0')})

    for exp in expenses:
        if exp.get('created_at'):
            try:
                created = datetime.fromisoformat(exp['created_at'].replace('Z', '+00:00'))
                hour = f"{created.hour:02d}:00"

                hourly_totals[hour]['count'] += 1
                hourly_totals[hour]['amount'] += Decimal(str(exp['amount']))
            except Exception:
                pass

    for hour in sorted(hourly_totals):
        data = hourly_totals[hour]
        writer.writerow([hour, data['count'], float(data['amount'])])

    return response
