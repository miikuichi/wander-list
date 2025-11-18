from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from .models import SavingsGoal, SavingsTransaction
from .forms import SavingsGoalForm, AddSavingsForm
from decimal import Decimal
import logging
from supabase_service import get_service_client

logger = logging.getLogger(__name__)


def savings_goals_view(request):
    """
    Display savings goals page with all CRUD functionality.
    GET: Shows list of goals and create form
    POST: Creates new goal (Supabase)
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to access savings goals")
        messages.error(request, "⚠️ Please log in to view your savings goals.")
        return redirect('login:login_page')
    
    try:
        if request.method == 'POST':
            form = SavingsGoalForm(request.POST)
            
            if form.is_valid():
                try:
                    # Create goal in Supabase instead of SQLite
                    supabase = get_service_client()
                    
                    goal_data = {
                        'user_id': user_id,
                        'name': form.cleaned_data['name'],
                        'target_amount': str(form.cleaned_data['target_amount']),
                        'current_amount': '0.00',
                        'description': form.cleaned_data.get('description', ''),
                        'target_date': form.cleaned_data['target_date'].isoformat() if form.cleaned_data.get('target_date') else None,
                        'status': 'active'
                    }
                    
                    response = supabase.table('savings_goals').insert(goal_data).execute()
                    
                    if response.data:
                        goal_name = response.data[0]['name']
                        logger.info(f"Savings goal created in Supabase: user_id={user_id}, name={goal_name}")
                        messages.success(request, f"✅ Savings goal '{goal_name}' created successfully!")
                    else:
                        raise Exception("No data returned from Supabase insert")
                    
                    return redirect('savings_goals:goals')
                    
                except Exception as e:
                    logger.error(f"Error creating savings goal for user {user_id}: {e}", exc_info=True)
                    messages.error(request, f"⚠️ Failed to create savings goal: {str(e)}")
            else:
                logger.warning(f"Invalid savings goal form submission: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"⚠️ {error}")
        else:
            form = SavingsGoalForm()
        
        # Fetch all goals for this user from Supabase
        try:
            supabase = get_service_client()
            
            # Get active goals
            active_response = supabase.table('savings_goals')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .order('created_at', desc=True)\
                .execute()
            
            active_goals = active_response.data if active_response.data else []
            
            # Calculate progress for each active goal
            for goal in active_goals:
                current = Decimal(str(goal.get('current_amount', 0)))
                target = Decimal(str(goal.get('target_amount', 1)))  # Avoid division by zero
                
                goal['progress_percentage'] = float((current / target) * 100) if target > 0 else 0
                goal['is_complete'] = current >= target
                goal['remaining_amount'] = target - current
            
            # Get completed goals
            completed_response = supabase.table('savings_goals')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('status', 'completed')\
                .order('completed_at', desc=True)\
                .execute()
            
            completed_goals = completed_response.data if completed_response.data else []
            
            # Calculate progress for completed goals too
            for goal in completed_goals:
                current = Decimal(str(goal.get('current_amount', 0)))
                target = Decimal(str(goal.get('target_amount', 1)))
                
                goal['progress_percentage'] = float((current / target) * 100) if target > 0 else 0
                goal['is_complete'] = True  # Already completed
                goal['remaining_amount'] = target - current
            
            # Calculate statistics
            total_target = sum(Decimal(str(g.get('target_amount', 0))) for g in active_goals)
            total_saved = sum(Decimal(str(g.get('current_amount', 0))) for g in active_goals)
            
            logger.info(f"Retrieved {len(active_goals)} active goals from Supabase for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error fetching savings goals from Supabase for user {user_id}: {e}", exc_info=True)
            active_goals = []
            completed_goals = []
            total_target = Decimal('0.00')
            total_saved = Decimal('0.00')
            messages.error(request, "⚠️ Failed to load savings goals from database.")
        
        # Get wallet balance to show available funds for savings
        try:
            from expenses.views import get_wallet_balance
            wallet_info = get_wallet_balance(user_id)
            available_for_savings = wallet_info['closing_balance']
        except Exception as e:
            logger.warning(f"Could not fetch wallet balance: {e}")
            available_for_savings = Decimal('0.00')
        
        context = {
            'form': form,
            'active_goals': active_goals,
            'completed_goals': completed_goals,
            'total_target': total_target,
            'total_saved': total_saved,
            'available_for_savings': available_for_savings,
        }
        
        return render(request, 'savings_goals/goals.html', context)
        
    except Exception as e:
        logger.error(f"Unexpected error in savings_goals_view for user {user_id}: {e}", exc_info=True)
        messages.error(request, "⚠️ An unexpected error occurred. Please try again.")
        return redirect('dashboard')


def edit_goal_view(request, goal_id):
    """
    Edit an existing savings goal.
    GET: Returns goal data (for modal)
    POST: Updates the goal
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to edit savings goal")
        messages.error(request, "⚠️ Please log in to edit savings goals.")
        return redirect('login:login_page')
    
    try:
        goal = get_object_or_404(SavingsGoal, id=goal_id, user_id=user_id)
        
        if request.method == 'POST':
            form = SavingsGoalForm(request.POST, instance=goal)
            
            if form.is_valid():
                try:
                    form.save()
                    logger.info(f"Savings goal updated: user_id={user_id}, goal_id={goal_id}")
                    messages.success(request, f"✅ Savings goal '{goal.name}' updated successfully!")
                    return redirect('savings_goals:goals')
                    
                except Exception as e:
                    logger.error(f"Error updating savings goal {goal_id} for user {user_id}: {e}", exc_info=True)
                    messages.error(request, f"⚠️ Failed to update savings goal: {str(e)}")
            else:
                logger.warning(f"Invalid edit form for goal {goal_id}: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"⚠️ {error}")
        
        return redirect('savings_goals:goals')
        
    except SavingsGoal.DoesNotExist:
        logger.warning(f"User {user_id} attempted to edit non-existent goal {goal_id}")
        messages.error(request, "⚠️ Savings goal not found or you don't have permission to edit it.")
        return redirect('savings_goals:goals')
    except Exception as e:
        logger.error(f"Unexpected error editing goal {goal_id} for user {user_id}: {e}", exc_info=True)
        messages.error(request, "⚠️ An unexpected error occurred while editing the goal.")
        return redirect('savings_goals:goals')


def delete_goal_view(request, goal_id):
    """
    Delete a savings goal (Supabase).
    POST only: Deletes the goal from database
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to delete savings goal")
        messages.error(request, "⚠️ Please log in to delete savings goals.")
        return redirect('login:login_page')
    
    if request.method != 'POST':
        logger.warning(f"GET request to delete goal {goal_id} rejected")
        return redirect('savings_goals:goals')
    
    try:
        supabase = get_service_client()
        
        # Get goal from Supabase first to get the name
        goal_response = supabase.table('savings_goals')\
            .select('name')\
            .eq('id', goal_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not goal_response.data:
            logger.warning(f"User {user_id} attempted to delete non-existent goal {goal_id}")
            messages.error(request, "⚠️ Savings goal not found or you don't have permission to delete it.")
            return redirect('savings_goals:goals')
        
        goal_name = goal_response.data[0]['name']
        
        # Delete from Supabase
        supabase.table('savings_goals')\
            .delete()\
            .eq('id', goal_id)\
            .eq('user_id', user_id)\
            .execute()
        
        logger.info(f"Savings goal deleted from Supabase: user_id={user_id}, goal_id={goal_id}, name={goal_name}")
        messages.success(request, f"✅ Savings goal '{goal_name}' deleted successfully!")
        
    except Exception as e:
        logger.error(f"Error deleting goal {goal_id} for user {user_id}: {e}", exc_info=True)
        messages.error(request, f"⚠️ Failed to delete savings goal: {str(e)}")
    
    return redirect('savings_goals:goals')


def add_savings_view(request, goal_id):
    """
    Add savings to a goal (Supabase).
    POST: Adds amount to goal's current savings
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to add savings")
        messages.error(request, "⚠️ Please log in to add savings.")
        return redirect('login:login_page')
    
    if request.method != 'POST':
        logger.warning(f"GET request to add savings to goal {goal_id} rejected")
        return redirect('savings_goals:goals')
    
    try:
        supabase = get_service_client()
        
        # Get goal from Supabase
        goal_response = supabase.table('savings_goals')\
            .select('*')\
            .eq('id', goal_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not goal_response.data:
            logger.warning(f"User {user_id} attempted to add savings to non-existent goal {goal_id}")
            messages.error(request, "⚠️ Savings goal not found or you don't have permission.")
            return redirect('savings_goals:goals')
        
        goal = goal_response.data[0]
        
        amount_str = request.POST.get('amount', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Validation
        if not amount_str:
            messages.error(request, "⚠️ Amount is required.")
            return redirect('savings_goals:goals')
        
        try:
            amount = Decimal(amount_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid amount format: {amount_str}")
            messages.error(request, "⚠️ Please enter a valid amount.")
            return redirect('savings_goals:goals')
        
        if amount <= 0:
            messages.error(request, "⚠️ Amount must be greater than zero.")
            return redirect('savings_goals:goals')
        
        if amount > Decimal('999999999.99'):
            messages.error(request, "⚠️ Amount is too large. Maximum is ₱999,999,999.99")
            return redirect('savings_goals:goals')
        
        # Add savings
        try:
            current_amount = Decimal(str(goal['current_amount']))
            new_amount = current_amount + amount
            target_amount = Decimal(str(goal['target_amount']))
            
            # Check if user has enough in wallet balance
            from expenses.views import get_wallet_balance
            wallet_info = get_wallet_balance(user_id)
            
            if amount > wallet_info['closing_balance']:
                messages.error(request, 
                             f"⚠️ Insufficient funds! You only have ₱{wallet_info['closing_balance']:.2f} available in your wallet. "
                             f"Cannot transfer ₱{amount:.2f} to savings.")
                return redirect('savings_goals:goals')
            
            # Create expense record to deduct from wallet (Category: Savings Transfer)
            from datetime import datetime, timezone as tz
            expense_data = {
                'user_id': user_id,
                'amount': float(amount),
                'category': 'Savings',
                'date': datetime.now(tz.utc).date().isoformat(),
                'notes': f"Transfer to '{goal['name']}' savings goal" + (f" - {notes}" if notes else ""),
                'created_at': datetime.now(tz.utc).isoformat(),
                'updated_at': datetime.now(tz.utc).isoformat()
            }
            
            # Insert expense (deducts from wallet)
            expense_response = supabase.table('expenses').insert(expense_data).execute()
            
            if not expense_response.data:
                raise Exception("Failed to create expense record")
            
            # Determine if goal is now completed
            new_status = 'completed' if new_amount >= target_amount else 'active'
            
            # Update goal in Supabase with new amount and status
            update_data = {
                'current_amount': str(new_amount),
                'status': new_status
            }
            
            # Add completed_at timestamp if just completed
            if new_status == 'completed' and goal['status'] != 'completed':
                from datetime import datetime
                update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            update_response = supabase.table('savings_goals')\
                .update(update_data)\
                .eq('id', goal_id)\
                .execute()
            
            # Record transaction in Supabase
            transaction_data = {
                'goal_id': goal_id,
                'amount': str(amount),
                'transaction_type': 'add',
                'notes': notes
            }
            supabase.table('savings_transactions').insert(transaction_data).execute()
            
            logger.info(f"Added ₱{amount} to goal {goal_id} for user {user_id}. Deducted from wallet balance.")
            
            # Show success message with wallet balance info
            remaining_balance = wallet_info['closing_balance'] - amount
            messages.success(request, 
                           f"✅ Added ₱{amount:.2f} to '{goal['name']}'! "
                           f"Current savings: ₱{new_amount:.2f}. "
                           f"Remaining wallet balance: ₱{remaining_balance:.2f}")
            
            # Calculate progress percentage for milestone alerts
            target_amount = Decimal(str(goal['target_amount']))
            progress_percentage = float((new_amount / target_amount) * 100) if target_amount > 0 else 0
            
            # Get user email from Supabase
            try:
                user_response = supabase.table('login_user').select('email').eq('id', user_id).execute()
                user_email = user_response.data[0]['email'] if user_response.data else None
            except Exception as e:
                logger.warning(f"Could not fetch user email for alerts: {e}")
                user_email = None
            
            # Lazy import to avoid circular imports
            from notifications.services import GoalAlertService
            
            # Check and send milestone alerts
            GoalAlertService.check_and_send_milestone_alerts(
                goal_id=goal_id,
                user_id=user_id,
                progress_percentage=progress_percentage,
                user_email=user_email
            )
            
            # Check deadline alerts
            if goal.get('target_date'):
                from datetime import datetime
                target_date = datetime.fromisoformat(goal['target_date']).date() if isinstance(goal['target_date'], str) else goal['target_date']
                GoalAlertService.check_deadline_alerts(
                    goal_id=goal_id,
                    user_id=user_id,
                    target_date=target_date,
                    goal_name=goal['name'],
                    user_email=user_email
                )
            
            # Check if goal is now complete
            if new_amount >= target_amount and goal['status'] != 'completed':
                messages.success(request, f"🎉 Congratulations! You've reached your goal for '{goal['name']}'!")
            
        except Exception as e:
            logger.error(f"Error adding savings to goal {goal_id}: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to add savings: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error adding savings to goal {goal_id}: {e}", exc_info=True)
        messages.error(request, "⚠️ An unexpected error occurred. Please try again.")
    
    return redirect('savings_goals:goals')


def achieve_goal_view(request, goal_id):
    """
    Mark a goal as achieved/completed.
    POST: Updates goal status to completed
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to mark goal as achieved")
        messages.error(request, "⚠️ Please log in to mark goals as achieved.")
        return redirect('login:login_page')
    
    if request.method != 'POST':
        logger.warning(f"GET request to achieve goal {goal_id} rejected")
        return redirect('savings_goals:goals')
    
    try:
        goal = get_object_or_404(SavingsGoal, id=goal_id, user_id=user_id)
        
        try:
            goal.mark_complete()
            logger.info(f"Goal {goal_id} marked as achieved by user {user_id}")
            messages.success(request, f"🎉 Congratulations! '{goal.name}' marked as achieved!")
            
        except Exception as e:
            logger.error(f"Error marking goal {goal_id} as achieved: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to mark goal as achieved: {str(e)}")
        
    except SavingsGoal.DoesNotExist:
        logger.warning(f"User {user_id} attempted to achieve non-existent goal {goal_id}")
        messages.error(request, "⚠️ Savings goal not found or you don't have permission.")
    except Exception as e:
        logger.error(f"Unexpected error achieving goal {goal_id}: {e}", exc_info=True)
        messages.error(request, "⚠️ An unexpected error occurred. Please try again.")
    
    return redirect('savings_goals:goals')


def reset_goal_view(request, goal_id):
    """
    Reset a goal's progress to zero.
    POST: Resets current_amount to 0
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        logger.warning("Unauthenticated user attempted to reset goal")
        messages.error(request, "⚠️ Please log in to reset goals.")
        return redirect('login:login_page')
    
    if request.method != 'POST':
        logger.warning(f"GET request to reset goal {goal_id} rejected")
        return redirect('savings_goals:goals')
    
    try:
        goal = get_object_or_404(SavingsGoal, id=goal_id, user_id=user_id)
        
        try:
            # Record reset transaction
            if goal.current_amount > 0:
                SavingsTransaction.objects.create(
                    goal=goal,
                    amount=goal.current_amount,
                    transaction_type='reset',
                    notes='Goal progress reset to zero'
                )
            
            goal.reset_progress()
            logger.info(f"Goal {goal_id} reset by user {user_id}")
            messages.success(request, f"✅ '{goal.name}' progress reset to zero.")
            
        except Exception as e:
            logger.error(f"Error resetting goal {goal_id}: {e}", exc_info=True)
            messages.error(request, f"⚠️ Failed to reset goal: {str(e)}")
        
    except SavingsGoal.DoesNotExist:
        logger.warning(f"User {user_id} attempted to reset non-existent goal {goal_id}")
        messages.error(request, "⚠️ Savings goal not found or you don't have permission.")
    except Exception as e:
        logger.error(f"Unexpected error resetting goal {goal_id}: {e}", exc_info=True)
        messages.error(request, "⚠️ An unexpected error occurred. Please try again.")
    
    return redirect('savings_goals:goals')
