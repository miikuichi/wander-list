from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_datetime

from supabase_service import get_service_client


@require_http_methods(["GET", "POST"])
def reminders_page(request):
    """Reminders and Notifications page with create + list.

    - GET: list current user's reminders
    - POST: create a new reminder for the current session user or edit an existing one

    Supabase table: reminders (per your screenshot) with columns:
      id, user_id, title, due_at, frequency, next_run_at, pre_alert_offset_days,
      is_completed, notify_email, notify_in_app
    """
    # Ensure session has user_id (middleware already does a redirect if not set)
    user_id = request.session.get('user_id')

    supabase = get_service_client()

    if request.method == 'POST':
        reminder_id = request.POST.get('reminder_id')  # For editing
        title = (request.POST.get('title') or '').strip()
        due_at_raw = request.POST.get('due_at') or None
        frequency = (request.POST.get('frequency') or '').strip() or None
        pre_alert_offset_days = request.POST.get('pre_alert_offset_days')
        notify_email = request.POST.get('notify_email') == 'on'
        notify_in_app = request.POST.get('notify_in_app') == 'on'

        # Basic validation
        if not title:
            messages.error(request, 'Title is required.')
            return redirect('reminders:home')

        # 🛑 ADD THIS VALIDATION BLOCK
        # Enforce due_at if the frequency is 'once'
        if frequency == 'once' and not due_at_raw:
            messages.error(request, 'Date and Time is required for a "Once" reminder.')
            return redirect('reminders:home')
        # 🛑 END OF ADDED BLOCK

        # Parse due_at to ISO 8601 if provided (expects 'YYYY-MM-DDTHH:MM' or similar)
        due_at_iso = None
        if due_at_raw:
            try:
                dt = parse_datetime(due_at_raw)
                if dt is None:
                    # Accept date-only; let DB accept timestamptz casting if string
                    due_at_iso = due_at_raw
                else:
                    due_at_iso = dt.isoformat()
            except Exception:
                due_at_iso = due_at_raw

        # Convert pre_alert_offset_days to int or None
        try:
            pre_alert_offset_days = int(pre_alert_offset_days) if pre_alert_offset_days not in (None, '',) else None
        except ValueError:
            pre_alert_offset_days = None

        if reminder_id:  # Editing existing reminder
            payload = {
                'title': title,
                'due_at': due_at_iso,
                'frequency': frequency,
                'notify_email': notify_email,
                'notify_in_app': notify_in_app,
            }
            try:
                supabase.table('reminders') \
                    .update(payload) \
                    .eq('id', reminder_id) \
                    .eq('user_id', user_id) \
                    .execute()
                messages.success(request, 'Reminder updated.')
            except Exception as e:
                messages.error(request, f'Failed to update reminder: {e}')
        else:  # Creating new reminder
            payload = {
                'user_id': user_id,
                'title': title,
                'due_at': due_at_iso,
                'frequency': frequency,
                'pre_alert_offset_days': pre_alert_offset_days,
                'notify_email': notify_email,
                'notify_in_app': notify_in_app,
                # is_completed defaults to false in DB
            }
            try:
                supabase.table('reminders').insert(payload).execute()
                messages.success(request, 'Reminder created.')
            except Exception as e:
                messages.error(request, f'Failed to create reminder: {e}')

        return redirect('reminders:home')

    # GET: list reminders for this user
    try:
        res = supabase.table('reminders') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('is_completed', desc=False) \
            .order('due_at', desc=False) \
            .execute()
        reminders = res.data if hasattr(res, 'data') else (res.get('data') if isinstance(res, dict) else [])
        # Parse due_at strings to datetime objects for template rendering
        for reminder in reminders:
            if reminder.get('due_at'):
                parsed_dt = parse_datetime(reminder['due_at'])
                if parsed_dt:
                    reminder['due_at'] = parsed_dt
    except Exception as e:
        messages.error(request, f'Failed to load reminders: {e}')
        reminders = []

    context = {
        'reminders': reminders,
    }
    return render(request, 'reminders/reminders.html', context)


@require_http_methods(["POST"]) # We use POST for security reasons (prevents CSRF tokens issues)
def delete_reminder(request, reminder_id):
    """
    Deletes a specific reminder from the Supabase 'reminders' table.
    """
    user_id = request.session.get('user_id')
    supabase = get_service_client()

    if not user_id:
        messages.error(request, 'You must be logged in to delete reminders.')
        return redirect('reminders:home')

    try:
        # CRITICAL: Use the DELETE method and ensure RLS is handled by Supabase
        # We also filter by user_id to prevent users from deleting others' reminders
        supabase.table('reminders') \
            .delete() \
            .eq('id', reminder_id) \
            .eq('user_id', user_id) \
            .execute()
            
        # The result data will be empty if successful
        messages.success(request, 'Reminder successfully deleted.')

    except Exception as e:
        messages.error(request, f'Failed to delete reminder: {e}')

    # Redirect back to the reminders page after deletion attempt
    return redirect('reminders:home')



@require_http_methods(["GET", "POST"])
def edit_reminder(request, reminder_id):
    """
    Handles both fetching a reminder for editing (GET) and processing the update (POST).
    """
    user_id = request.session.get('user_id')
    supabase = get_service_client()
    
    # 1. Fetch the existing reminder data
    try:
        # Fetch the single reminder, ensuring it belongs to the current user
        res = supabase.table('reminders') \
            .select('*') \
            .eq('id', reminder_id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()
        
        # Extract the single record (Supabase client often returns results in .data)
        reminder = res.data
        
        if not reminder:
            messages.error(request, 'Reminder not found or access denied.')
            return redirect('reminders:home')

    except Exception:
        # This catches errors if the row count is not 1 (e.g., reminder doesn't exist)
        messages.error(request, 'Error loading reminder details.')
        return redirect('reminders:home')
    
    # --- HANDLE POST REQUEST (UPDATE) ---
    if request.method == 'POST':
        # Retrieve all fields, same as your creation view
        title = (request.POST.get('title') or '').strip()
        due_at_raw = request.POST.get('due_at') or None
        frequency = (request.POST.get('frequency') or '').strip() or None
        
        # Checkbox handling (must check for existence since unchecked boxes aren't sent)
        notify_email = request.POST.get('notify_email') == 'on'
        notify_in_app = request.POST.get('notify_in_app') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'reminders/reminders.html', {'editing_reminder': reminder})

        # 🛑 ADD THIS VALIDATION BLOCK
        # Enforce due_at if the frequency is 'once'
        if frequency == 'once' and not due_at_raw:
            messages.error(request, 'Date and Time is required for a "Once" reminder.')
            # Ensure 'editing_reminder' is still available for re-rendering
            return render(request, 'reminders/reminders.html', {'editing_reminder': reminder})
        # 🛑 END OF ADDED BLOCK

        # Date Parsing (reusing your existing logic from reminders_page)
        due_at_iso = None
        if due_at_raw:
             try:
                dt = parse_datetime(due_at_raw)
                due_at_iso = dt.isoformat() if dt else due_at_raw
             except Exception:
                due_at_iso = due_at_raw

        # Build the payload for the UPDATE query
        payload = {
            'title': title,
            'due_at': due_at_iso,
            'frequency': frequency,
            'notify_email': notify_email,
            'notify_in_app': notify_in_app,
            # user_id should NOT be updated
        }
        
        # Execute the UPDATE in Supabase
        try:
            supabase.table('reminders') \
                .update(payload) \
                .eq('id', reminder_id) \
                .eq('user_id', user_id) \
                .execute()
                
            messages.success(request, 'Reminder updated successfully.')
            return redirect('reminders:home')
            
        except Exception as e:
            messages.error(request, f'Failed to update reminder: {e}')
            # Re-render the form with error
            return render(request, 'reminders/reminders.html', {'editing_reminder': reminder})


    # --- HANDLE GET REQUEST (PRE-FILL FORM) ---
    # Pass the reminder object to the template to pre-fill the form fields
    context = {
        'editing_reminder': reminder,
    }
    return render(request, 'reminders/reminders.html', context)