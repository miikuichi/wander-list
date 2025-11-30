from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import BudgetAlertForm, MAJOR_CATEGORIES
from supabase_service import get_service_client
from datetime import datetime, timezone
import logging
from django.utils.html import escape
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.template.loader import render_to_string
from login.decorators import require_authentication, require_owner
from audit_logs.services import log_create, log_update, log_delete, log_budget_breach, log_alert_triggered

logger = logging.getLogger(__name__)


@require_authentication
def alerts_page(request):
    """
    Displays budget alerts page and handles creation of new alerts.
    Uses SIMPLIFIED Supabase schema (no separate categories table).
    Category is stored directly in budget_alerts table as VARCHAR.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.warning(request, "⚠️ Please log in to manage budget alerts.")
        return redirect('login:login_page')
    
    try:
        supabase = get_service_client()
        
        # Handle form submission for creating a new budget alert
        if request.method == "POST":
            form = BudgetAlertForm(request.POST, user=user_id)
            
            if form.is_valid():
                try:
                    cleaned_data = form.cleaned_data
                    final_category_name = cleaned_data['final_category_name']
                    
                    # Create budget alert in Supabase (SIMPLIFIED - no categories table)
                    now = datetime.now(timezone.utc).isoformat()
                    alert_data = {
                        'user_id': user_id,
                        'category': final_category_name,  # Direct column, not FK
                        'amount_limit': float(cleaned_data['amount_limit']),
                        'threshold_percent': cleaned_data['threshold_percent'],
                        'notify_dashboard': cleaned_data.get('notify_dashboard', True),
                        'notify_email': cleaned_data.get('notify_email', False),
                        'notify_push': cleaned_data.get('notify_push', False),
                        'active': cleaned_data.get('active', True),
                        'created_at': now,
                        'updated_at': now
                    }
                    
                    supabase.table('budget_alerts').insert(alert_data).execute()
                    
                    logger.info(f"Budget alert created: user={user_id}, category={final_category_name}, "
                              f"limit=₱{cleaned_data['amount_limit']}")
                    messages.success(request, 
                                   f"✅ Budget alert created for '{final_category_name}' "
                                   f"(₱{cleaned_data['amount_limit']:.2f})!")
                    return redirect("budget_alerts:alerts_page")
                    
                except Exception as e:
                    logger.error(f"Failed to create budget alert: {e}", exc_info=True)
                    messages.error(request, f"⚠️ Failed to create budget alert: {str(e)}")
        else:
            form = BudgetAlertForm(user=user_id)
        
        # Fetch budget alerts from Supabase (SIMPLIFIED - category is direct column)
        alerts_response = supabase.table('budget_alerts')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('active', True)\
            .order('created_at', desc=True)\
            .execute()
        
        alerts = alerts_response.data if alerts_response.data else []
        
        # Calculate current spending for each alert
        for alert in alerts:
            try:
                category_name = alert['category']  # Direct column access
                
                # Get total spending for this category
                expenses_response = supabase.table('expenses')\
                    .select('amount')\
                    .eq('user_id', user_id)\
                    .eq('category', category_name)\
                    .execute()
                
                current_spending = sum(exp['amount'] for exp in expenses_response.data) if expenses_response.data else 0
                alert['current_spending'] = current_spending
                alert['percent_used'] = (current_spending / alert['amount_limit'] * 100) if alert['amount_limit'] > 0 else 0
                alert['is_triggered'] = alert['percent_used'] >= alert['threshold_percent']
                alert['remaining'] = alert['amount_limit'] - current_spending
                
            except Exception as e:
                logger.error(f"Error calculating spending for alert {alert['id']}: {e}")
                alert['current_spending'] = 0
                alert['percent_used'] = 0
                alert['is_triggered'] = False
                alert['remaining'] = alert['amount_limit']
        
        logger.info(f"Loaded {len(alerts)} budget alerts for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error loading budget alerts page: {e}", exc_info=True)
        messages.error(request, "⚠️ Failed to load budget alerts.")
        alerts = []
        form = BudgetAlertForm(user=user_id)
    
    return render(request, "budget_alerts/alerts.html", {
        "form": form,
        "alerts": alerts,
        "major_categories": MAJOR_CATEGORIES
    })


def edit_alert(request, id):
    """
    AJAX modal edit view (returns JSON).
    Generates the form HTML inline and includes a valid CSRF token.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '⚠️ Please log in to edit alerts.'}, status=403)

    try:
        supabase = get_service_client()

        # Fetch alert
        alert_response = supabase.table('budget_alerts') \
            .select('*') \
            .eq('id', id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()

        if not alert_response.data:
            return JsonResponse({'success': False, 'message': 'Alert not found.'}, status=404)

        alert_data = alert_response.data

        if request.method == "POST":
            # Build mock instance for form validation (as you had)
            class MockAlert:
                def __init__(self, data):
                    self.id = data['id']
                    self.amount_limit = data['amount_limit']
                    self.threshold_percent = data['threshold_percent']
                    self.notify_dashboard = data['notify_dashboard']
                    self.notify_email = data['notify_email']
                    self.notify_push = data['notify_push']
                    self.active = data['active']
                    self.category = type('obj', (object,), {'name': data.get('category', '')})

            mock_instance = MockAlert(alert_data)
            form = BudgetAlertForm(request.POST, user=user_id, instance=mock_instance)

            if form.is_valid():
                cleaned = form.cleaned_data
                final_category_name = cleaned['final_category_name']
                now = datetime.now(timezone.utc).isoformat()

                update_data = {
                    'category': final_category_name,
                    'amount_limit': float(cleaned['amount_limit']),
                    'threshold_percent': cleaned['threshold_percent'],
                    'notify_dashboard': cleaned.get('notify_dashboard', True),
                    'notify_email': cleaned.get('notify_email', False),
                    'notify_push': cleaned.get('notify_push', False),
                    'active': cleaned.get('active', True),
                    'updated_at': now,
                }

                supabase.table('budget_alerts') \
                    .update(update_data) \
                    .eq('id', id) \
                    .eq('user_id', user_id) \
                    .execute()

                return JsonResponse({'success': True, 'message': '✅ Budget alert updated successfully!'})

            else:
                # Return validation errors as JSON (frontend will show them)
                errors = {f: [escape(e) for e in errs] for f, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})

        # GET: build and return the form HTML string with a valid CSRF token
        form = BudgetAlertForm(user=user_id)
        # pre-fill form fields using the alert data
        form.fields['amount_limit'].initial = alert_data.get('amount_limit')
        form.fields['threshold_percent'].initial = alert_data.get('threshold_percent')
        form.fields['notify_dashboard'].initial = alert_data.get('notify_dashboard')
        form.fields['notify_email'].initial = alert_data.get('notify_email')
        form.fields['notify_push'].initial = alert_data.get('notify_push')

        # Get a valid CSRF token for this request
        csrf_token = get_token(request)

        # Build form action using reverse (safer than hardcoding)
        form_action = reverse('edit_alert', kwargs={'id': id})
        # Render form.as_p() into the modal body (simple approach)
        form_html = f"""
        <form id="editAlertForm" method="post" action="{form_action}">
          <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
          <div class="modal-header">
            <h5 class="modal-title">Edit Alert: {escape(alert_data.get('category',''))}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            {form.as_p()}
          </div>
          <div class="modal-footer">
            <button type="submit" class="btn btn-primary">Save Changes</button>
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          </div>
        </form>
        """

        return JsonResponse({'html': form_html})

    except Exception as e:
        logger.error(f"Edit alert error: {e}", exc_info=True)
        # Return a JSON error message — keep the stacktrace in server logs
        return JsonResponse({'success': False, 'message': '⚠️ Server error while loading alert.'}, status=500)


def delete_alert(request, id):
    """
    Handles deleting a budget alert from Supabase.
    SIMPLIFIED - category is direct column.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.warning(request, "⚠️ Please log in to delete budget alerts.")
        return redirect('login:login_page')
    
    if request.method == 'POST':
        try:
            supabase = get_service_client()
            
            # Verify ownership before deleting
            verify = supabase.table('budget_alerts')\
                .select('id, category')\
                .eq('id', id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not verify.data:
                messages.error(request, "⚠️ Budget alert not found or you don't have permission to delete it.")
                return redirect("budget_alerts:alerts_page")
            
            category_name = verify.data[0]['category']  # Direct column access
            
            # Delete the alert
            supabase.table('budget_alerts')\
                .delete()\
                .eq('id', id)\
                .eq('user_id', user_id)\
                .execute()
            
            logger.info(f"Budget alert deleted: id={id}, category={category_name}, user_id={user_id}")
            messages.success(request, f"✅ Budget alert for '{category_name}' deleted successfully!")
            
        except Exception as e:
            logger.error(f"Failed to delete budget alert: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to delete budget alert: {str(e)}")
    
    return redirect("budget_alerts:alerts_page")


@require_authentication
def budget_analysis_view(request):
    """
    Budget analysis page with comparisons, predictions, and health scores.
    """
    user_id = request.session.get('user_id')
    
    from .services import get_budget_vs_actual, calculate_category_health_score, predict_budget_breach
    from datetime import date
    from calendar import monthrange
    
    # Get current month info
    today = date.today()
    start_of_month = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day
    
    # Get budget vs actual comparison
    comparison = get_budget_vs_actual(user_id, start_of_month, today)
    
    # Calculate health scores and predictions for each category
    analysis_data = []
    for category, data in comparison.items():
        health = calculate_category_health_score(user_id, category, data['budget'])
        prediction = predict_budget_breach(user_id, category, data['budget'], days_remaining)
        
        analysis_data.append({
            'category': category,
            'budget': data['budget'],
            'actual': data['actual'],
            'variance': data['variance'],
            'variance_percent': data['variance_percent'],
            'usage_percent': data['usage_percent'],
            'status': data['status'],
            'health': health,
            'prediction': prediction
        })
    
    # Sort by health score (worst first)
    analysis_data.sort(key=lambda x: x['health']['score'])
    
    # Calculate overall statistics
    total_budget = sum(d['budget'] for d in analysis_data)
    total_actual = sum(d['actual'] for d in analysis_data)
    overall_usage = float((total_actual / total_budget * 100)) if total_budget > 0 else 0.0
    
    categories_over = sum(1 for d in analysis_data if d['status'] == 'over')
    categories_warning = sum(1 for d in analysis_data if d['health']['level'] in ['warning', 'critical'])
    
    context = {
        'analysis_data': analysis_data,
        'total_budget': total_budget,
        'total_actual': total_actual,
        'overall_usage': overall_usage,
        'categories_over': categories_over,
        'categories_warning': categories_warning,
        'days_remaining': days_remaining,
        'current_month': today.strftime('%B %Y'),
    }
    
    return render(request, 'budget_alerts/analysis.html', context)


@require_authentication
def budget_predictions_api(request):
    """
    API endpoint for budget predictions data (JSON).
    """
    user_id = request.session.get('user_id')
    
    from .services import predict_budget_breach
    from datetime import date
    from calendar import monthrange
    from django.http import JsonResponse
    
    today = date.today()
    days_in_month = monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day
    
    # Get all active budget alerts
    supabase = get_service_client()
    alerts_response = supabase.table('budget_alerts_budgetalert')\
        .select('*, category:category_id(*)')\
        .eq('user_id', user_id)\
        .eq('active', True)\
        .execute()
    
    predictions = []
    for alert in alerts_response.data:
        category_name = alert['category']['name']
        budget_limit = alert['amount_limit']
        
        prediction = predict_budget_breach(user_id, category_name, budget_limit, days_remaining)
        
        predictions.append({
            'category': category_name,
            'budget': float(budget_limit),
            'will_breach': prediction['will_breach'],
            'predicted_spending': float(prediction['predicted_spending']),
            'predicted_date': prediction['predicted_date'].isoformat() if prediction['predicted_date'] else None,
            'daily_average': float(prediction['daily_average']),
            'recommended_daily_limit': float(prediction['recommended_daily_limit']),
            'confidence': prediction['confidence'],
            'message': prediction['message']
        })
    
    return JsonResponse({'predictions': predictions})


@require_authentication
def snooze_alert_view(request, alert_id):
    """
    Snooze an alert for a specified duration.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    user_id = request.session.get('user_id')
    duration = request.POST.get('duration', '24h')  # 1h, 24h, 7d
    
    from django.utils import timezone
    from datetime import timedelta
    
    # Parse duration
    duration_map = {
        '1h': timedelta(hours=1),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
    }
    
    snooze_delta = duration_map.get(duration, timedelta(hours=24))
    snooze_until = timezone.now() + snooze_delta
    
    try:
        supabase = get_service_client()
        
        # Verify ownership and update
        result = supabase.table('budget_alerts_budgetalert')\
            .update({'snoozed_until': snooze_until.isoformat()})\
            .eq('id', alert_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not result.data:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        
        messages.success(request, f"✅ Alert snoozed for {duration}")
        return JsonResponse({
            'success': True,
            'snoozed_until': snooze_until.isoformat(),
            'message': f'Alert snoozed for {duration}'
        })
    
    except Exception as e:
        logger.error(f"Failed to snooze alert: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@require_authentication
def unsnooze_alert_view(request, alert_id):
    """
    Remove snooze from an alert.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    user_id = request.session.get('user_id')
    
    try:
        supabase = get_service_client()
        
        result = supabase.table('budget_alerts_budgetalert')\
            .update({'snoozed_until': None})\
            .eq('id', alert_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not result.data:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        
        messages.success(request, "✅ Alert unsnoozed")
        return JsonResponse({'success': True, 'message': 'Alert unsnoozed'})
    
    except Exception as e:
        logger.error(f"Failed to unsnooze alert: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@require_authentication
def alert_history_view(request):
    """
    Display alert trigger history for the user.
    """
    user_id = request.session.get('user_id')
    
    from datetime import datetime, timedelta
    
    # Get filter parameters
    days = int(request.GET.get('days', 30))
    category = request.GET.get('category', '')
    severity = request.GET.get('severity', '')
    
    try:
        supabase = get_service_client()
        
        # Build query
        query = supabase.table('budget_alerts_alerthistory')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('triggered_at', desc=True)
        
        # Apply filters
        if days > 0:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            query = query.gte('triggered_at', start_date)
        
        if category:
            query = query.eq('category', category)
        
        if severity:
            query = query.eq('severity', severity)
        
        history_response = query.limit(100).execute()
        
        # Get statistics
        stats_query = supabase.table('budget_alerts_alerthistory')\
            .select('severity, threshold_level')\
            .eq('user_id', user_id)
        
        if days > 0:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            stats_query = stats_query.gte('triggered_at', start_date)
        
        stats_response = stats_query.execute()
        
        # Calculate statistics
        total_alerts = len(stats_response.data)
        severity_counts = {
            'info': 0,
            'warning': 0,
            'danger': 0,
            'critical': 0
        }
        
        for record in stats_response.data:
            severity_key = record.get('severity', 'info')
            severity_counts[severity_key] = severity_counts.get(severity_key, 0) + 1
        
        # Get unique categories for filter dropdown
        categories = set(record['category'] for record in history_response.data)
        
        context = {
            'history': history_response.data,
            'total_alerts': total_alerts,
            'severity_counts': severity_counts,
            'categories': sorted(categories),
            'selected_days': days,
            'selected_category': category,
            'selected_severity': severity,
        }
        
        return render(request, 'budget_alerts/alert_history.html', context)
    
    except Exception as e:
        logger.error(f"Failed to load alert history: {e}", exc_info=True)
        messages.error(request, f"⚠️ Failed to load alert history: {str(e)}")
        return redirect('budget_alerts:alerts_page')
