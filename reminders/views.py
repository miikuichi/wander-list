from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_datetime

from supabase_service import get_service_client
from login.decorators import require_authentication, require_owner
from audit_logs.services import log_create, log_update, log_delete


@require_authentication
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
                log_update(
                    user_id=str(user_id),
                    resource_type="reminder",
                    resource_id=str(reminder_id),
                    metadata=payload,
                    request=request,
                )
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
                result = supabase.table('reminders').insert(payload).execute()
                reminder_id = result.data[0]['id'] if result.data else None
                if reminder_id:
                    log_create(
                        user_id=str(user_id),
                        resource_type="reminder",
                        resource_id=str(reminder_id),
                        metadata=payload,
                        request=request,
                    )
                messages.success(request, 'Reminder created.')
                
                # NEW: Send notifications if requested
                if (notify_email or notify_in_app) and reminder_id:
                    try:
                        # Get user email
                        user_response = supabase.table('login_user').select('email').eq('id', user_id).execute()
                        user_email = user_response.data[0]['email'] if user_response.data else None
                        
                        # Import notification service
                        import sys
                        import os
                        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from notifications.services import NotificationService
                        
                        # Determine notification types
                        notification_types = []
                        if notify_in_app:
                            notification_types.append('dashboard')
                        if notify_email:
                            notification_types.append('email')
                        
                        # Format due date for message
                        due_date_msg = f" due {due_at_iso}" if due_at_iso else ""
                        
                        # Send notification
                        NotificationService.send_notification(
                            user_id=user_id,
                            title=f"📅 Reminder Set: {title}",
                            message=f"Your reminder '{title}' has been created{due_date_msg}.\nFrequency: {frequency or 'Once'}",
                            category='reminder',
                            notification_types=notification_types,
                            related_object_type='reminder',
                            related_object_id=reminder_id,
                            user_email=user_email,
                        )
                    except Exception as notif_error:
                        import logging
                        logging.getLogger(__name__).error(f"Failed to send reminder notification: {notif_error}")
                
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
        supabase.table('reminders') \
            .delete() \
            .eq('id', reminder_id) \
            .eq('user_id', user_id) \
            .execute()
        log_delete(
            user_id=str(user_id),
            resource_type="reminder",
            resource_id=str(reminder_id),
            metadata={},
            request=request,
        )
        messages.success(request, 'Reminder successfully deleted.')

    except Exception as e:
        messages.error(request, f'Failed to delete reminder: {e}')

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
        res = supabase.table('reminders') \
            .select('*') \
            .eq('id', reminder_id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()
        
        reminder = res.data
        
        if not reminder:
            messages.error(request, 'Reminder not found or access denied.')
            return redirect('reminders:home')

    except Exception:
        messages.error(request, 'Error loading reminder details.')
        return redirect('reminders:home')
    
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        due_at_raw = request.POST.get('due_at') or None
        frequency = (request.POST.get('frequency') or '').strip() or None
        
        notify_email = request.POST.get('notify_email') == 'on'
        notify_in_app = request.POST.get('notify_in_app') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'reminders/reminders.html', {'editing_reminder': reminder})

        if frequency == 'once' and not due_at_raw:
            messages.error(request, 'Date and Time is required for a "Once" reminder.')
            return render(request, 'reminders/reminders.html', {'editing_reminder': reminder})

        due_at_iso = None
        if due_at_raw:
             try:
                dt = parse_datetime(due_at_raw)
                due_at_iso = dt.isoformat() if dt else due_at_raw
             except Exception:
                due_at_iso = due_at_raw

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
            log_update(
                user_id=str(user_id),
                resource_type="reminder",
                resource_id=str(reminder_id),
                metadata=payload,
                request=request,
            )
            messages.success(request, 'Reminder updated successfully.')
            return redirect('reminders:home')
            
        except Exception as e:
            messages.error(request, f'Failed to update reminder: {e}')
            return render(request, 'reminders/reminders.html', {'editing_reminder': reminder})

    context = {
        'editing_reminder': reminder,
    }
    return render(request, 'reminders/reminders.html', context)
