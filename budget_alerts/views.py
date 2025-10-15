from django.contrib import messages
from django.shortcuts import render, redirect
from supabase_service import get_service_client
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Default categories to create for new users
DEFAULT_CATEGORIES = ["Food", "Transport", "Leisure", "Bills", "School Supplies"]

def alerts_page(request):
    """
    Display budget alerts page and handle CRUD operations with Supabase.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    supabase = get_service_client()
    
    try:
        # Fetch categories for this user
        cat_response = supabase.table('budget_alerts_category')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('name')\
            .execute()
        
        categories = cat_response.data if cat_response.data else []
        
        # Create default categories if none exist
        if not categories:
            for name in DEFAULT_CATEGORIES:
                # Note: budget_alerts_category only has id, name, user_id (no created_at)
                supabase.table('budget_alerts_category').insert({
                    'user_id': user_id,
                    'name': name
                }).execute()
            
            # Refetch categories
            cat_response = supabase.table('budget_alerts_category')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('name')\
                .execute()
            categories = cat_response.data if cat_response.data else []
        
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
        categories = []
        messages.error(request, "⚠️ Failed to load categories.")
    
    # Handle form submission for creating a new budget alert
    if request.method == "POST":
        try:
            amount_limit = request.POST.get('amount_limit')
            category_id = request.POST.get('category')
            threshold_percent = request.POST.get('threshold_percent', 80)
            notify_dashboard = request.POST.get('notify_dashboard') == 'on'
            notify_email = request.POST.get('notify_email') == 'on'
            notify_push = request.POST.get('notify_push') == 'on'
            
            # Validate
            if not amount_limit or not category_id:
                messages.error(request, "⚠️ Amount and category are required.")
                return redirect("alerts_page")
            
            # Insert into Supabase (explicitly set timestamps)
            now = datetime.now(timezone.utc).isoformat()
            
            supabase.table('budget_alerts_budgetalert').insert({
                'user_id': user_id,
                'category_id': int(category_id),
                'amount_limit': float(amount_limit),
                'threshold_percent': int(threshold_percent),
                'notify_dashboard': notify_dashboard,
                'notify_email': notify_email,
                'notify_push': notify_push,
                'active': True,
                'created_at': now,
                'updated_at': now
            }).execute()
            
            messages.success(request, "✅ Budget alert saved successfully!")
            return redirect("alerts_page")
            
        except Exception as e:
            logger.error(f"Failed to create budget alert: {e}")
            messages.error(request, f"⚠️ Failed to save alert: {str(e)}")
            return redirect("alerts_page")
    
    # Fetch active budget alerts for this user with category info
    try:
        alerts_response = supabase.table('budget_alerts_budgetalert')\
            .select('*, budget_alerts_category(*)')\
            .eq('user_id', user_id)\
            .eq('active', True)\
            .order('created_at', desc=True)\
            .execute()
        
        alerts = alerts_response.data if alerts_response.data else []
        
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {e}")
        alerts = []
        messages.error(request, "⚠️ Failed to load budget alerts.")
    
    return render(request, "budget_alerts/alerts.html", {
        "alerts": alerts,
        "categories": categories 
    })

def edit_alert(request, id):
    """
    Update an existing budget alert in Supabase.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    if request.method == "POST":
        try:
            amount_limit = request.POST.get('amount_limit')
            category_id = request.POST.get('category')
            threshold_percent = request.POST.get('threshold_percent', 80)
            notify_dashboard = request.POST.get('notify_dashboard') == 'on'
            notify_email = request.POST.get('notify_email') == 'on'
            notify_push = request.POST.get('notify_push') == 'on'
            
            # Validate
            if not amount_limit or not category_id:
                messages.error(request, "⚠️ Amount and category are required.")
                return redirect("alerts_page")
            
            # Update in Supabase
            supabase = get_service_client()
            now = datetime.now(timezone.utc).isoformat()
            
            supabase.table('budget_alerts_budgetalert').update({
                'category_id': int(category_id),
                'amount_limit': float(amount_limit),
                'threshold_percent': int(threshold_percent),
                'notify_dashboard': notify_dashboard,
                'notify_email': notify_email,
                'notify_push': notify_push,
                'active': True,
                'updated_at': now
            }).eq('id', id).eq('user_id', user_id).execute()
            
            messages.success(request, "✅ Budget alert updated successfully!")
            return redirect("alerts_page")
            
        except Exception as e:
            logger.error(f"Failed to update budget alert: {e}")
            messages.error(request, f"⚠️ Failed to update alert: {str(e)}")
            return redirect("alerts_page")
    
    return redirect("alerts_page")

def delete_alert(request, id):
    """
    Delete a budget alert from Supabase.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    try:
        supabase = get_service_client()
        supabase.table('budget_alerts_budgetalert')\
            .delete()\
            .eq('id', id)\
            .eq('user_id', user_id)\
            .execute()
        
        messages.success(request, "✅ Budget alert deleted successfully!")
        
    except Exception as e:
        logger.error(f"Failed to delete budget alert: {e}")
        messages.error(request, f"⚠️ Failed to delete alert: {str(e)}")
    
    return redirect('alerts_page')

