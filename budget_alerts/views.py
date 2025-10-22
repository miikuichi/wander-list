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

logger = logging.getLogger(__name__)


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
    
    return redirect("alerts_page")


