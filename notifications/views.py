from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .services import NotificationService
from .models import UserNotificationPreference
from login.models import User
import logging

logger = logging.getLogger(__name__)


def notifications_dashboard(request):
    """Display user's notifications dashboard."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, "⚠️ Please log in to view notifications.")
        return redirect('login:login_page')
    
    try:
        # Get user notifications
        all_notifications = NotificationService.get_user_notifications(
            user_id=user_id,
            unread_only=False,
            limit=100
        )
        
        unread_notifications = [n for n in all_notifications if n.status != 'read']
        
        # Get user preferences
        prefs = NotificationService.get_user_preferences(user_id)
        
        # Get user email for test button
        user = User.objects.filter(id=user_id).first()
        user_email = user.email if user else request.session.get('email', '')
        
        context = {
            'notifications': all_notifications,
            'unread_count': len(unread_notifications),
            'preferences': prefs,
            'user_email': user_email,
        }
        
        return render(request, 'notifications/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading notifications dashboard for user {user_id}: {e}")
        messages.error(request, "⚠️ Failed to load notifications.")
        return redirect('dashboard')


def mark_notification_read(request, notification_id):
    """Mark a notification as read."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    if request.method == 'POST':
        try:
            success = NotificationService.mark_notification_read(notification_id)
            
            if success:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
                
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


def notification_preferences(request):
    """View and update notification preferences."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        messages.error(request, "⚠️ Please log in to manage preferences.")
        return redirect('login:login_page')
    
    try:
        prefs = NotificationService.get_user_preferences(user_id)
        
        if request.method == 'POST':
            # Update preferences
            prefs.email_enabled = request.POST.get('email_enabled') == 'on'
            prefs.email_budget_alerts = request.POST.get('email_budget_alerts') == 'on'
            prefs.email_goal_milestones = request.POST.get('email_goal_milestones') == 'on'
            prefs.email_goal_deadlines = request.POST.get('email_goal_deadlines') == 'on'
            prefs.email_reminders = request.POST.get('email_reminders') == 'on'
            
            prefs.push_enabled = request.POST.get('push_enabled') == 'on'
            prefs.push_budget_alerts = request.POST.get('push_budget_alerts') == 'on'
            prefs.push_goal_milestones = request.POST.get('push_goal_milestones') == 'on'
            prefs.push_goal_deadlines = request.POST.get('push_goal_deadlines') == 'on'
            prefs.push_reminders = request.POST.get('push_reminders') == 'on'
            
            prefs.save()
            
            messages.success(request, "✅ Notification preferences updated successfully!")
            return redirect('notifications:preferences')
        
        context = {
            'preferences': prefs,
        }
        
        return render(request, 'notifications/preferences.html', context)
        
    except Exception as e:
        logger.error(f"Error managing preferences for user {user_id}: {e}")
        messages.error(request, "⚠️ Failed to load preferences.")
        return redirect('dashboard')


def get_unread_count(request):
    """API endpoint to get unread notification count (for navbar badge)."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return JsonResponse({'count': 0})
    
    try:
        notifications = NotificationService.get_user_notifications(
            user_id=user_id,
            unread_only=True,
            limit=100
        )
        
        return JsonResponse({'count': len(notifications)})
        
    except Exception as e:
        logger.error(f"Error getting unread count for user {user_id}: {e}")
        return JsonResponse({'count': 0})


def get_recent_notifications(request):
    """API endpoint to get recent notifications for navbar dropdown."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return JsonResponse({'notifications': []})
    
    try:
        notifications = NotificationService.get_user_notifications(
            user_id=user_id,
            unread_only=True,
            limit=10
        )
        
        notifications_data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'category': n.category,
            'created_at': n.created_at.strftime('%b %d, %I:%M %p'),
            'icon': get_notification_icon(n.category)
        } for n in notifications]
        
        return JsonResponse({'notifications': notifications_data})
        
    except Exception as e:
        logger.error(f"Error getting recent notifications for user {user_id}: {e}")
        return JsonResponse({'notifications': []})


def get_notification_icon(category):
    """Get icon for notification category."""
    icons = {
        'budget_alert': '💰',
        'goal_milestone': '🎯',
        'goal_deadline': '⏰',
        'goal_achieved': '🎉',
        'reminder': '📅',
        'expense': '💸',
    }
    return icons.get(category, '🔔')


def send_test_email(request):
    """Send a test email notification to the current user."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    if request.method == 'POST':
        try:
            # Get user email
            user = User.objects.filter(id=user_id).first()
            user_email = user.email if user else request.session.get('email')
            
            if not user_email:
                return JsonResponse({
                    'success': False, 
                    'error': 'No email address found for your account'
                }, status=400)
            
            # Send test notification
            result = NotificationService.send_notification(
                user_id=user_id,
                title='💰 PisoHeroes Email Test',
                message='If you\'re reading this email, your email notification system is working perfectly! 🎉\n\n'
                        'This is a test notification from PisoHeroes to verify that:\n'
                        '✓ Gmail SMTP is configured correctly\n'
                        '✓ Email notifications can be sent\n'
                        '✓ HTML templates are rendering properly\n\n'
                        'You can now receive notifications for:\n'
                        '• Budget alerts\n'
                        '• Savings goal milestones\n'
                        '• Goal deadlines\n'
                        '• Expense reminders\n\n'
                        'Next step: Try creating a savings goal and adding savings to trigger a milestone alert!',
                category='system',
                notification_types=['email', 'dashboard'],
                user_email=user_email
            )
            
            if result.get('email'):
                log = result['email']
                if log.status == 'sent':
                    return JsonResponse({
                        'success': True,
                        'message': f'Test email sent to {user_email}! Check your inbox (and spam folder).',
                        'notification_id': log.id
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Email failed: {log.error_message}'
                    }, status=500)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No email result returned'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error sending test email for user {user_id}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


def mark_all_as_read(request):
    """Mark all unread notifications as read for the current user."""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    if request.method == 'POST':
        try:
            # Get all unread notifications for the user
            unread_notifications = NotificationService.get_user_notifications(
                user_id=user_id,
                unread_only=True,
                limit=1000
            )
            
            # Mark each as read
            marked_count = 0
            for notification in unread_notifications:
                if NotificationService.mark_notification_read(notification.id):
                    marked_count += 1
            
            return JsonResponse({
                'success': True,
                'marked_count': marked_count,
                'message': f'Marked {marked_count} notification(s) as read'
            })
                
        except Exception as e:
            logger.error(f"Error marking all notifications as read for user {user_id}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


