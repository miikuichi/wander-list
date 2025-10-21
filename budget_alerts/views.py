from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import BudgetAlertForm, MAJOR_CATEGORIES
from supabase_service import get_service_client
from datetime import datetime, timezone
import logging

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
    Handles editing an existing budget alert in Supabase.
    SIMPLIFIED - category is direct column in budget_alerts.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.warning(request, "⚠️ Please log in to edit budget alerts.")
        return redirect('login:login_page')
    
    try:
        supabase = get_service_client()
        
        # Fetch the alert from Supabase (SIMPLIFIED - no JOIN needed)
        alert_response = supabase.table('budget_alerts')\
            .select('*')\
            .eq('id', id)\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        if not alert_response.data:
            messages.error(request, "⚠️ Budget alert not found or you don't have permission to edit it.")
            return redirect("budget_alerts:alerts_page")
        
        alert_data = alert_response.data
        
        if request.method == "POST":
            # Create a mock instance for form validation
            class MockAlert:
                def __init__(self, data):
                    self.id = data['id']
                    self.amount_limit = data['amount_limit']
                    self.threshold_percent = data['threshold_percent']
                    self.notify_dashboard = data['notify_dashboard']
                    self.notify_email = data['notify_email']
                    self.notify_push = data['notify_push']
                    self.active = data['active']
                    self.category = type('obj', (object,), {'name': data['category']})
            
            mock_instance = MockAlert(alert_data)
            form = BudgetAlertForm(request.POST, user=user_id, instance=mock_instance)
            
            if form.is_valid():
                try:
                    cleaned_data = form.cleaned_data
                    final_category_name = cleaned_data['final_category_name']
                    
                    # Update budget alert (SIMPLIFIED - direct category column)
                    now = datetime.now(timezone.utc).isoformat()
                    update_data = {
                        'category': final_category_name,  # Direct column update
                        'amount_limit': float(cleaned_data['amount_limit']),
                        'threshold_percent': cleaned_data['threshold_percent'],
                        'notify_dashboard': cleaned_data.get('notify_dashboard', True),
                        'notify_email': cleaned_data.get('notify_email', False),
                        'notify_push': cleaned_data.get('notify_push', False),
                        'active': cleaned_data.get('active', True),
                        'updated_at': now
                    }
                    
                    supabase.table('budget_alerts')\
                        .update(update_data)\
                        .eq('id', id)\
                        .eq('user_id', user_id)\
                        .execute()
                    
                    logger.info(f"Budget alert updated: id={id}, category={final_category_name}")
                    messages.success(request, "✅ Budget alert updated successfully!")
                    return redirect("budget_alerts:alerts_page")
                    
                except Exception as e:
                    logger.error(f"Failed to update budget alert: {e}", exc_info=True)
                    messages.error(request, f"⚠️ Failed to update budget alert: {str(e)}")
        else:
            # Pre-populate form with existing data
            mock_instance = type('obj', (object,), {
                'id': alert_data['id'],
                'amount_limit': alert_data['amount_limit'],
                'threshold_percent': alert_data['threshold_percent'],
                'notify_dashboard': alert_data['notify_dashboard'],
                'notify_email': alert_data['notify_email'],
                'notify_push': alert_data['notify_push'],
                'active': alert_data['active'],
                'category': type('obj', (object,), {'name': alert_data['category']})
            })
            form = BudgetAlertForm(user=user_id, instance=mock_instance)
        
        return render(request, "budget_alerts/alerts.html", {
            "form": form,
            "alert": alert_data,
            "editing": True
        })
        
    except Exception as e:
        logger.error(f"Error editing budget alert: {e}", exc_info=True)
        messages.error(request, "⚠️ Failed to load budget alert for editing.")
        return redirect("budget_alerts:alerts_page")


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
    
    return redirect('budget_alerts:alerts_page')

