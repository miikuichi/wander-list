from django.shortcuts import render, redirect
from django.contrib import messages
from supabase_service import get_service_client
from datetime import datetime
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
            
            # Insert into Supabase
            supabase = get_service_client()
            supabase.table('expenses').insert({
                'user_id': user_id,
                'amount': float(amount),
                'category': category,
                'date': date,
                'notes': notes
            }).execute()
            
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
        
    except Exception as e:
        logger.error(f"Failed to fetch expenses: {e}")
        recent_expenses = []
        messages.error(request, "⚠️ Failed to load expenses from database.")
    
    context = {
        'categories': CATEGORIES,
        'recent_expenses': recent_expenses,
    }
    return render(request, 'expenses/expenses.html', context)
