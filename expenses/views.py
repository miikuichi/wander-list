from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic.edit import DeleteView
from supabase_service import get_service_client
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Hardcoded categories as requested
CATEGORIES = ["Food", "Transport", "Leisure", "Bills", "School Supplies", "Shopping", "Healthcare", "Entertainment", "Other"]


def expenses_view(request):
    """
    Displays the expenses page and handles new expense submissions using Supabase.
    GET: Renders the page with recent expenses from Supabase.
    POST: Validates and saves the Expense to Supabase then redirects (PRG).
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    if request.method == 'POST':
        # Handle new expense submission
        try:
            amount = request.POST.get('amount')
            category = request.POST.get('category')
            date = request.POST.get('date')
            notes = request.POST.get('notes', '')
            
            # Validate inputs
            if not amount or not category or not date:
                messages.error(request, "⚠️ Amount, category, and date are required.")
                return redirect('expenses')
            
            # Insert into Supabase with explicit timestamps
            supabase = get_service_client()
            now = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table('expenses').insert({
                'user_id': user_id,
                'amount': float(amount),
                'category': category,
                'date': date,
                'notes': notes,
                'created_at': now,
                'updated_at': now
            }).execute()
            
            # Log success for debugging
            logger.info(f"Expense added: user_id={user_id}, amount={amount}, category={category}, result={result.data}")
            messages.success(request, "✅ Expense added successfully!")
            return redirect('expenses')
            
        except Exception as e:
            logger.error(f"Failed to add expense: {e}")
            messages.error(request, f"⚠️ Failed to add expense: {str(e)}")
            return redirect('expenses')
    
    # GET: Fetch expenses for this user from Supabase
    try:
        supabase = get_service_client()
        response = supabase.table('expenses')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('date', desc=True)\
            .order('created_at', desc=True)\
            .limit(50)\
            .execute()
        
        recent_expenses = response.data if response.data else []
        logger.info(f"Fetched {len(recent_expenses)} expenses for user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Failed to fetch expenses for user_id={user_id}: {e}", exc_info=True)
        recent_expenses = []
        messages.warning(request, f"⚠️ Failed to load expenses: {str(e)}")
    
    context = {
        'categories': CATEGORIES,
        'recent_expenses': recent_expenses,
    }
    return render(request, 'expenses/expenses.html', context)


def delete_expense(request, id):
    """
    Delete a single expense record from the 'expenses' table in Supabase.
    This function should be called via a POST request from the template (e.g., a delete button).
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        # Redirect if the user is not logged in
        return redirect('login:login_page')
    
    try:
        supabase = get_service_client()
        
        # --- Supabase Deletion Logic ---
        # The key is to chain .delete() and .execute()
        supabase.table('expenses')\
            .delete()\
            .eq('id', id)\
            .eq('user_id', user_id)\
            .execute()
        
        messages.success(request, "✅ Expense deleted successfully!")
        
    except Exception as e:
        logger.error(f"Failed to delete expense ID {id}: {e}")
        messages.error(request, f"⚠️ Failed to delete expense: {str(e)}")
    
    # Always redirect back to the main expenses view after the operation
    return redirect('expenses')


def edit_expense(request, id):
    """
    Update an existing expense in Supabase using the POST-Redirect-GET pattern,
    modeled after the structure of the budget_alerts edit function.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    if request.method == "POST":
        try:
            # 1. Get expense data from POST request
            amount = request.POST.get('amount')
            category = request.POST.get('category')
            date = request.POST.get('date')
            notes = request.POST.get('notes', '')
            
            # 2. Validate
            if not amount or not category or not date:
                messages.error(request, "⚠️ Amount, category, and date are required.")
                return redirect("expenses") # Redirect to main expense page
            
            # 3. Update in Supabase
            supabase = get_service_client()
            now = datetime.now(timezone.utc).isoformat()
            
            update_payload = {
                'amount': float(amount),
                'category': category,
                'date': date,
                'notes': notes,
                'updated_at': now
            }
            
            supabase.table('expenses')\
                .update(update_payload)\
                .eq('id', id)\
                .eq('user_id', user_id)\
                .execute()
            
            messages.success(request, "✅ Expense updated successfully!")
            return redirect("expenses") # Redirect to main expense page
            
        except Exception as e:
            logger.error(f"Failed to update expense ID {id}: {e}")
            messages.error(request, f"⚠️ Failed to update expense: {str(e)}")
            return redirect("expenses") # Redirect to main expense page
    
    # If a GET request is made to this URL (e.g., direct navigation), redirect to the main list.
    return redirect("expenses")

