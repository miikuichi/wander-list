from django.shortcuts import render, redirect
from django.contrib import messages
from supabase_service import get_service_client
from datetime import datetime, timezone, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Hardcoded categories as requested - matching budget_alerts major categories
CATEGORIES = ["Food", "Transport", "Leisure", "Bills", "School Supplies", "Shopping", "Healthcare", "Entertainment", "Other"]


def get_daily_allowance_remaining(user_id):
    """
    Get the remaining daily allowance for a user today.
    """
    try:
        supabase = get_service_client()
        
        # Get user's daily allowance from Supabase users table
        user_response = supabase.table('users')\
            .select('daily_allowance')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        daily_allowance = Decimal(str(user_response.data.get('daily_allowance', '500.00')))
        
        # Get today's expenses
        today = date.today().isoformat()
        expenses_response = supabase.table('expenses')\
            .select('amount')\
            .eq('user_id', user_id)\
            .eq('date', today)\
            .execute()
        
        today_spending = sum(Decimal(str(exp['amount'])) for exp in expenses_response.data) if expenses_response.data else Decimal('0.00')
        
        remaining = daily_allowance - today_spending
        
        logger.info(f"Daily allowance check: user={user_id}, allowance=₱{daily_allowance}, "
                   f"spent=₱{today_spending}, remaining=₱{remaining}")
        
        return {
            'daily_allowance': daily_allowance,
            'today_spending': today_spending,
            'remaining': remaining
        }
        
    except Exception as e:
        logger.error(f"Error calculating daily allowance: {e}", exc_info=True)
        return {
            'daily_allowance': Decimal('500.00'),
            'today_spending': Decimal('0.00'),
            'remaining': Decimal('500.00')
        }


def get_category_budget_status(user_id, category_name):
    """
    Check if expense would exceed category budget limit.
    Returns budget info and whether the category has a budget alert.
    """
    try:
        supabase = get_service_client()
        
        # Get budget alert for this category
        alert_response = supabase.table('budget_alerts')\
            .select('*, budget_categories!inner(*)')\
            .eq('user_id', user_id)\
            .eq('budget_categories.name', category_name)\
            .eq('active', True)\
            .execute()
        
        if not alert_response.data:
            return None  # No budget alert for this category
        
        alert = alert_response.data[0]
        amount_limit = Decimal(str(alert['amount_limit']))
        
        # Get current spending for this category
        expenses_response = supabase.table('expenses')\
            .select('amount')\
            .eq('user_id', user_id)\
            .eq('category', category_name)\
            .execute()
        
        current_spending = sum(Decimal(str(exp['amount'])) for exp in expenses_response.data) if expenses_response.data else Decimal('0.00')
        
        remaining = amount_limit - current_spending
        percent_used = (current_spending / amount_limit * 100) if amount_limit > 0 else 0
        
        logger.info(f"Category budget check: category={category_name}, "
                   f"limit=₱{amount_limit}, spent=₱{current_spending}, "
                   f"remaining=₱{remaining}, used={percent_used:.1f}%")
        
        return {
            'alert_id': alert['id'],
            'amount_limit': amount_limit,
            'current_spending': current_spending,
            'remaining': remaining,
            'percent_used': percent_used,
            'threshold_percent': alert['threshold_percent']
        }
        
    except Exception as e:
        logger.error(f"Error checking category budget: {e}", exc_info=True)
        return None


def expenses_view(request):
    """
    Displays the expenses page and handles new expense submissions using Supabase.
    GET: Renders the page with recent expenses from Supabase.
    POST: Validates and saves the Expense to Supabase then redirects (PRG).
    Now includes:
    - Daily allowance checking (expenses deducted from daily allowance)
    - Category budget limit checking
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    # Get daily allowance info for display
    allowance_info = get_daily_allowance_remaining(user_id)
    
    if request.method == 'POST':
        # Handle new expense submission
        try:
            amount = request.POST.get('amount')
            category = request.POST.get('category')
            date_str = request.POST.get('date')
            notes = request.POST.get('notes', '')
            
            # Validation 1: Check required fields
            if not amount or not category or not date_str:
                messages.error(request, "⚠️ Amount, category, and date are required.")
                return redirect('expenses:expenses')
            
            # Validation 2: Check if amount is a valid number
            try:
                amount_decimal = Decimal(amount)
            except (ValueError, TypeError):
                messages.error(request, "⚠️ Amount must be a valid number.")
                return redirect('expenses:expenses')
            
            # Validation 3: Check if amount is positive
            if amount_decimal <= 0:
                messages.error(request, "⚠️ Amount must be greater than zero.")
                return redirect('expenses:expenses')
            
            # Validation 4: Check if amount is reasonable (not too large)
            if amount_decimal > Decimal('999999999.99'):
                messages.error(request, "⚠️ Amount is too large. Maximum is ₱999,999,999.99.")
                return redirect('expenses:expenses')
            
            # Validation 5: Check if category is valid
            if category not in CATEGORIES:
                messages.error(request, f"⚠️ Invalid category. Please select from: {', '.join(CATEGORIES)}.")
                return redirect('expenses:expenses')
            
            # Validation 6: Check if date is valid format
            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "⚠️ Invalid date format. Please use YYYY-MM-DD.")
                return redirect('expenses:expenses')
            
            # NEW VALIDATION 7: Check if expense is for today and would exceed daily allowance
            if expense_date == date.today():
                if amount_decimal > allowance_info['remaining']:
                    messages.error(request, 
                                 f"🛑 Daily Allowance Exceeded! "
                                 f"This expense (₱{amount_decimal:.2f}) exceeds your remaining daily allowance "
                                 f"of ₱{allowance_info['remaining']:.2f}. "
                                 f"(Today's spending: ₱{allowance_info['today_spending']:.2f} / "
                                 f"₱{allowance_info['daily_allowance']:.2f})")
                    return redirect('expenses:expenses')
                
                # Warn if expense would use more than 80% of remaining allowance
                if amount_decimal > (allowance_info['remaining'] * Decimal('0.8')):
                    messages.warning(request,
                                   f"⚠️ Warning: This expense will use most of your remaining daily allowance "
                                   f"(₱{allowance_info['remaining'] - amount_decimal:.2f} left after this expense).")
            
            # NEW VALIDATION 8: Check category budget limits
            budget_status = get_category_budget_status(user_id, category)
            if budget_status:
                proposed_total = budget_status['current_spending'] + amount_decimal
                
                # Block if would exceed category budget limit
                if proposed_total > budget_status['amount_limit']:
                    messages.error(request,
                                 f"🛑 Category Budget Exceeded! "
                                 f"This expense (₱{amount_decimal:.2f}) exceeds the budget limit for '{category}'. "
                                 f"Current spending: ₱{budget_status['current_spending']:.2f} / "
                                 f"₱{budget_status['amount_limit']:.2f}. "
                                 f"Remaining: ₱{budget_status['remaining']:.2f}")
                    return redirect('expenses:expenses')
                
                # Warn if approaching threshold
                new_percent = (proposed_total / budget_status['amount_limit'] * 100)
                if new_percent >= budget_status['threshold_percent']:
                    messages.warning(request,
                                   f"⚠️ Budget Alert: Adding this expense will reach {new_percent:.1f}% "
                                   f"of your '{category}' budget (₱{proposed_total:.2f} / "
                                   f"₱{budget_status['amount_limit']:.2f}).")
            
            # All validations passed - Insert into Supabase
            supabase = get_service_client()
            now = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table('expenses').insert({
                'user_id': user_id,
                'amount': float(amount_decimal),
                'category': category,
                'date': date_str,
                'notes': notes.strip(),
                'created_at': now,
                'updated_at': now
            }).execute()
            
            # Log success for debugging
            logger.info(f"Expense added: user_id={user_id}, amount=₱{amount_decimal}, "
                       f"category={category}, date={date_str}")
            messages.success(request, f"✅ Expense of ₱{amount_decimal:.2f} added successfully!")
            
            return redirect('expenses:expenses')
            
        except Exception as e:
            logger.error(f"Failed to add expense: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to add expense: {str(e)}")
            return redirect('expenses:expenses')
    
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
        
        logger.info(f"Loaded {len(recent_expenses)} expenses for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to fetch expenses: {e}", exc_info=True)
        recent_expenses = []
        messages.error(request, "⚠️ Failed to load expenses from database.")
    
    context = {
        'categories': CATEGORIES,
        'recent_expenses': recent_expenses,
        'daily_allowance': allowance_info['daily_allowance'],
        'today_spending': allowance_info['today_spending'],
        'remaining_allowance': allowance_info['remaining'],
    }
    return render(request, 'expenses/expenses.html', context)


def edit_expense_view(request, expense_id):
    """
    Handles editing an existing expense.
    GET: Returns expense data as JSON for AJAX requests.
    POST: Updates the expense in Supabase.
    Now includes daily allowance and budget checking.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    supabase = get_service_client()
    
    if request.method == 'GET':
        # Fetch the expense to verify ownership
        try:
            response = supabase.table('expenses')\
                .select('*')\
                .eq('id', expense_id)\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            if response.data:
                from django.http import JsonResponse
                return JsonResponse(response.data)
            else:
                messages.error(request, "⚠️ Expense not found or you don't have permission to edit it.")
                return redirect('expenses:expenses')
                
        except Exception as e:
            logger.error(f"Failed to fetch expense for edit: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to fetch expense: {str(e)}")
            return redirect('expenses:expenses')
    
    elif request.method == 'POST':
        # Update the expense
        try:
            # Get the original expense first
            original = supabase.table('expenses')\
                .select('*')\
                .eq('id', expense_id)\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            if not original.data:
                messages.error(request, "⚠️ Expense not found or you don't have permission to edit it.")
                return redirect('expenses:expenses')
            
            original_data = original.data
            amount = request.POST.get('amount')
            category = request.POST.get('category')
            date_str = request.POST.get('date')
            notes = request.POST.get('notes', '')
            
            # Same validation as create
            if not amount or not category or not date_str:
                messages.error(request, "⚠️ Amount, category, and date are required.")
                return redirect('expenses:expenses')
            
            try:
                amount_decimal = Decimal(amount)
            except (ValueError, TypeError):
                messages.error(request, "⚠️ Amount must be a valid number.")
                return redirect('expenses:expenses')
            
            if amount_decimal <= 0:
                messages.error(request, "⚠️ Amount must be greater than zero.")
                return redirect('expenses:expenses')
            
            if amount_decimal > Decimal('999999999.99'):
                messages.error(request, "⚠️ Amount is too large. Maximum is ₱999,999,999.99.")
                return redirect('expenses:expenses')
            
            if category not in CATEGORIES:
                messages.error(request, f"⚠️ Invalid category. Please select from: {', '.join(CATEGORIES)}.")
                return redirect('expenses:expenses')
            
            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "⚠️ Invalid date format. Please use YYYY-MM-DD.")
                return redirect('expenses:expenses')
            
            # NEW: Check daily allowance if date is today
            if expense_date == date.today():
                allowance_info = get_daily_allowance_remaining(user_id)
                
                # Calculate what remaining would be if we remove old expense and add new one
                original_amount = Decimal(str(original_data['amount']))
                original_date = datetime.strptime(original_data['date'], '%Y-%m-%d').date()
                
                # If original was also today, add it back to remaining
                adjusted_remaining = allowance_info['remaining']
                if original_date == date.today():
                    adjusted_remaining += original_amount
                
                if amount_decimal > adjusted_remaining:
                    messages.error(request,
                                 f"🛑 Daily Allowance Exceeded! "
                                 f"This change (₱{amount_decimal:.2f}) exceeds your remaining daily allowance "
                                 f"of ₱{adjusted_remaining:.2f}.")
                    return redirect('expenses:expenses')
            
            # NEW: Check category budget
            budget_status = get_category_budget_status(user_id, category)
            if budget_status:
                # Subtract original amount if same category
                adjusted_current = budget_status['current_spending']
                if original_data['category'] == category:
                    adjusted_current -= Decimal(str(original_data['amount']))
                
                proposed_total = adjusted_current + amount_decimal
                
                if proposed_total > budget_status['amount_limit']:
                    messages.error(request,
                                 f"🛑 Category Budget Exceeded! "
                                 f"This change would exceed the budget limit for '{category}'. "
                                 f"Adjusted spending: ₱{adjusted_current:.2f}, "
                                 f"New total: ₱{proposed_total:.2f} / ₱{budget_status['amount_limit']:.2f}")
                    return redirect('expenses:expenses')
            
            # Update the expense
            now = datetime.now(timezone.utc).isoformat()
            result = supabase.table('expenses').update({
                'amount': float(amount_decimal),
                'category': category,
                'date': date_str,
                'notes': notes.strip(),
                'updated_at': now
            }).eq('id', expense_id).eq('user_id', user_id).execute()
            
            logger.info(f"Expense updated: id={expense_id}, user_id={user_id}, amount=₱{amount_decimal}")
            messages.success(request, f"✅ Expense updated successfully!")
            return redirect('expenses:expenses')
            
        except Exception as e:
            logger.error(f"Failed to update expense: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to update expense: {str(e)}")
            return redirect('expenses:expenses')


def delete_expense_view(request, expense_id):
    """
    Handles deleting an expense.
    POST only: Deletes the expense from Supabase.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login:login_page')
    
    if request.method == 'POST':
        try:
            supabase = get_service_client()
            
            # Verify ownership before deleting
            verify = supabase.table('expenses')\
                .select('id, amount, category')\
                .eq('id', expense_id)\
                .eq('user_id', user_id)\
                .execute()
            
            if not verify.data:
                messages.error(request, "⚠️ Expense not found or you don't have permission to delete it.")
                return redirect('expenses:expenses')
            
            # Delete the expense
            expense_data = verify.data[0]
            result = supabase.table('expenses')\
                .delete()\
                .eq('id', expense_id)\
                .eq('user_id', user_id)\
                .execute()
            
            logger.info(f"Expense deleted: id={expense_id}, user_id={user_id}")
            messages.success(request, f"✅ Expense deleted successfully!")
            return redirect('expenses:expenses')
            
        except Exception as e:
            logger.error(f"Failed to delete expense: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to delete expense: {str(e)}")
            return redirect('expenses:expenses')
    
    # Redirect if not POST
    return redirect('expenses:expenses')
