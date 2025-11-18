"""
Notification Service - Handles sending email, push, and dashboard notifications.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from typing import Optional, Dict, Any
import requests

from .models import NotificationLog, UserNotificationPreference, GoalAlert

logger = logging.getLogger(__name__)


class NotificationService:
    """Centralized service for sending notifications across different channels."""
    
    @staticmethod
    def get_user_preferences(user_id: int) -> UserNotificationPreference:
        """Get or create user notification preferences."""
        prefs, created = UserNotificationPreference.objects.get_or_create(
            user_id=user_id,
            defaults={
                'email_enabled': True,
                'push_enabled': False,
            }
        )
        return prefs
    
    @staticmethod
    def create_budget_alert_notification(
        user_id: int,
        category: str,
        spent: float,
        limit: float,
        percentage: float,
        threshold: int,
        user_email: str = None,
    ) -> Dict[str, Any]:
        """
        Create notification for budget alert when threshold is reached.
        
        Args:
            user_id: User ID from session
            category: Budget category name
            spent: Amount spent in category
            limit: Budget limit for category
            percentage: Percentage of budget used
            threshold: Threshold percentage that triggered alert
            user_email: User's email address for email notifications
        
        Returns:
            Dict with results for each notification type
        """
        # Determine severity emoji and message
        if percentage >= 100:
            emoji = "🚨"
            severity_text = "Budget exceeded!"
        elif percentage >= 90:
            emoji = "⚠️"
            severity_text = "Critical threshold reached!"
        elif percentage >= threshold:
            emoji = "💰"
            severity_text = f"Budget threshold reached ({threshold}%)"
        else:
            return {}  # Don't send notification if below threshold
        
        title = f"{emoji} Budget Alert: {category}"
        message = (
            f"{severity_text}\n\n"
            f"You've spent ₱{spent:,.2f} out of ₱{limit:,.2f} ({percentage:.1f}%).\n"
            f"{'Budget has been exceeded!' if percentage >= 100 else f'Remaining: ₱{(limit - spent):,.2f}'}"
        )
        
        # Get user preferences to determine notification channels
        prefs = NotificationService.get_user_preferences(user_id)
        notification_types = ['dashboard']  # Always create dashboard notification
        
        # Add email if user has it enabled
        if prefs.email_enabled and user_email:
            notification_types.append('email')
        
        # Add push if user has it enabled and has FCM token
        if prefs.push_enabled and prefs.fcm_token:
            notification_types.append('push')
        
        return NotificationService.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            category='budget_alert',
            notification_types=notification_types,
            related_object_type='budget_alert',
            related_object_id=None,  # Could store alert ID if needed
            user_email=user_email,
        )
    
    @staticmethod
    def send_notification(
        user_id: int,
        title: str,
        message: str,
        category: str,
        notification_types: list = None,
        related_object_type: str = None,
        related_object_id: int = None,
        user_email: str = None,
    ) -> Dict[str, Any]:
        """
        Send notification through multiple channels based on user preferences.
        
        Args:
            user_id: User ID from session
            title: Notification title
            message: Notification message body
            category: Category from NotificationLog.NOTIFICATION_CATEGORIES
            notification_types: List of types to send ['email', 'push', 'dashboard']
            related_object_type: Type of related object (e.g., 'savings_goal')
            related_object_id: ID of related object
            user_email: User's email address (required for email notifications)
        
        Returns:
            Dict with results for each notification type
        """
        if notification_types is None:
            notification_types = ['dashboard']  # Default to dashboard only
        
        prefs = NotificationService.get_user_preferences(user_id)
        results = {}
        
        # Send email notification
        if 'email' in notification_types and prefs.email_enabled and user_email:
            email_result = NotificationService._send_email(
                user_id=user_id,
                user_email=user_email,
                title=title,
                message=message,
                category=category,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
            )
            results['email'] = email_result
        
        # Send push notification
        if 'push' in notification_types and prefs.push_enabled and prefs.fcm_token:
            push_result = NotificationService._send_push(
                user_id=user_id,
                fcm_token=prefs.fcm_token,
                title=title,
                message=message,
                category=category,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
            )
            results['push'] = push_result
        
        # Create dashboard notification (always create)
        if 'dashboard' in notification_types:
            dashboard_result = NotificationService._create_dashboard_notification(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
            )
            results['dashboard'] = dashboard_result
        
        return results
    
    @staticmethod
    def _send_email(
        user_id: int,
        user_email: str,
        title: str,
        message: str,
        category: str,
        related_object_type: str = None,
        related_object_id: int = None,
    ) -> NotificationLog:
        """Send email notification."""
        log = NotificationLog.objects.create(
            user_id=user_id,
            notification_type='email',
            category=category,
            title=title,
            message=message,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
        )
        
        try:
            # Send email
            send_mail(
                subject=f"PisoHeroes - {title}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )
            
            log.mark_sent()
            logger.info(f"Email sent successfully to {user_email}: {title}")
            
        except Exception as e:
            log.mark_failed(e)
            logger.error(f"Failed to send email to {user_email}: {e}")
        
        return log
    
    @staticmethod
    def _send_email_via_supabase(
        user_id: int,
        user_email: str,
        title: str,
        message: str,
        category: str,
        related_object_type: str = None,
        related_object_id: int = None,
    ) -> NotificationLog:
        """Send email notification via Supabase Edge Function + Resend.
        
        This method uses a Supabase Edge Function to send emails through Resend API.
        Make sure you've deployed the Edge Function and set SUPABASE_FUNCTION_URL in settings.
        
        To use this method, update send_notification() to call _send_email_via_supabase
        instead of _send_email.
        """
        log = NotificationLog.objects.create(
            user_id=user_id,
            notification_type='email',
            category=category,
            title=title,
            message=message,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
        )
        
        try:
            # Get the base URL from settings
            from django.conf import settings
            supabase_url = getattr(settings, 'SUPABASE_FUNCTION_URL', None)
            supabase_key = getattr(settings, 'SUPABASE_ANON_KEY', None)
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_FUNCTION_URL and SUPABASE_ANON_KEY must be set in settings.py. "
                    "See EMAIL_SETUP_GUIDE.md for instructions."
                )
            
            # Build HTML email with better styling
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6; 
                        color: #1f2937; 
                        margin: 0;
                        padding: 0;
                        background-color: #f9fafb;
                    }}
                    .container {{ 
                        max-width: 600px; 
                        margin: 40px auto; 
                        background-color: white;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{ 
                        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
                        color: white; 
                        padding: 32px 24px; 
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                        font-weight: 600;
                    }}
                    .content {{ 
                        padding: 32px 24px;
                        background-color: white;
                    }}
                    .content h2 {{
                        color: #111827;
                        font-size: 24px;
                        margin-top: 0;
                        margin-bottom: 16px;
                    }}
                    .content p {{
                        color: #4b5563;
                        font-size: 16px;
                        line-height: 1.6;
                        margin-bottom: 24px;
                    }}
                    .button {{ 
                        display: inline-block; 
                        background-color: #4F46E5; 
                        color: white !important; 
                        padding: 14px 28px; 
                        text-decoration: none; 
                        border-radius: 8px;
                        font-weight: 500;
                        transition: background-color 0.2s;
                    }}
                    .button:hover {{
                        background-color: #4338CA;
                    }}
                    .footer {{ 
                        text-align: center; 
                        padding: 24px;
                        background-color: #f9fafb;
                        border-top: 1px solid #e5e7eb;
                    }}
                    .footer p {{
                        color: #6b7280; 
                        font-size: 14px;
                        margin: 8px 0;
                    }}
                    .footer a {{
                        color: #4F46E5;
                        text-decoration: none;
                    }}
                    .footer a:hover {{
                        text-decoration: underline;
                    }}
                    .category-badge {{
                        display: inline-block;
                        background-color: #EEF2FF;
                        color: #4F46E5;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                        text-transform: uppercase;
                        margin-bottom: 16px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>💰 PisoHeroes</h1>
                    </div>
                    <div class="content">
                        <span class="category-badge">{category.replace('_', ' ')}</span>
                        <h2>{title}</h2>
                        <p>{message}</p>
                        <a href="http://localhost:8000/notifications/" class="button">View in App →</a>
                    </div>
                    <div class="footer">
                        <p>You're receiving this because you have notifications enabled for PisoHeroes.</p>
                        <p><a href="http://localhost:8000/notifications/preferences/">Manage Email Preferences</a></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Call the Edge Function
            function_url = supabase_url.rstrip('/') + '/send-notification-email'
            
            response = requests.post(
                function_url,
                json={
                    'to': user_email,
                    'subject': f'PisoHeroes - {title}',
                    'html': html_message,
                },
                headers={
                    'Authorization': f'Bearer {supabase_key}',
                    'Content-Type': 'application/json',
                },
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                log.mark_sent()
                logger.info(f"Email sent successfully via Supabase Edge Function to {user_email}: {title}")
            else:
                error_msg = result.get('error', 'Unknown error from Edge Function')
                log.mark_failed(str(error_msg))
                logger.error(f"Edge Function failed to send email to {user_email}: {error_msg}")
        
        except Exception as e:
            log.mark_failed(str(e))
            logger.error(f"Failed to send email via Supabase Edge Function to {user_email}: {e}")
        
        return log
    
    @staticmethod
    def _send_push(
        user_id: int,
        fcm_token: str,
        title: str,
        message: str,
        category: str,
        related_object_type: str = None,
        related_object_id: int = None,
    ) -> NotificationLog:
        """Send push notification via Firebase Cloud Messaging."""
        log = NotificationLog.objects.create(
            user_id=user_id,
            notification_type='push',
            category=category,
            title=title,
            message=message,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
        )
        
        try:
            fcm_server_key = getattr(settings, 'FCM_SERVER_KEY', None)
            
            if not fcm_server_key:
                raise ValueError("FCM_SERVER_KEY not configured in settings")
            
            # FCM API endpoint
            url = "https://fcm.googleapis.com/fcm/send"
            
            headers = {
                "Authorization": f"key={fcm_server_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "to": fcm_token,
                "notification": {
                    "title": title,
                    "body": message,
                    "icon": "notification_icon",
                    "sound": "default",
                },
                "data": {
                    "category": category,
                    "related_object_type": related_object_type or "",
                    "related_object_id": str(related_object_id) if related_object_id else "",
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            log.mark_sent()
            logger.info(f"Push notification sent successfully: {title}")
            
        except Exception as e:
            log.mark_failed(e)
            logger.error(f"Failed to send push notification: {e}")
        
        return log
    
    @staticmethod
    def _create_dashboard_notification(
        user_id: int,
        title: str,
        message: str,
        category: str,
        related_object_type: str = None,
        related_object_id: int = None,
    ) -> NotificationLog:
        """Create dashboard notification (in-app notification)."""
        log = NotificationLog.objects.create(
            user_id=user_id,
            notification_type='dashboard',
            category=category,
            title=title,
            message=message,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            status='sent',  # Dashboard notifications are immediately available
            sent_at=timezone.now(),
        )
        
        logger.info(f"Dashboard notification created: {title}")
        return log
    
    @staticmethod
    def get_user_notifications(
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> list:
        """Get notifications for user's dashboard."""
        queryset = NotificationLog.objects.filter(
            user_id=user_id,
            notification_type='dashboard'
        )
        
        if unread_only:
            queryset = queryset.exclude(status='read')
        
        return list(queryset[:limit])
    
    @staticmethod
    def mark_notification_read(notification_id: int) -> bool:
        """Mark a notification as read."""
        try:
            notification = NotificationLog.objects.get(id=notification_id)
            notification.mark_read()
            return True
        except NotificationLog.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found")
            return False


class GoalAlertService:
    """Service for managing savings goal alerts."""
    
    @staticmethod
    def check_and_send_milestone_alerts(goal_id: int, user_id: int, progress_percentage: float, user_email: str = None):
        """
        Check if goal has reached a milestone and send alerts.
        
        Args:
            goal_id: Savings goal ID
            user_id: User ID
            progress_percentage: Current progress percentage (0-100)
            user_email: User's email address
        """
        milestones = [
            (25, 'milestone_25', '25% of your savings goal reached! 🎉'),
            (50, 'milestone_50', "Halfway there! You've saved 50%! 💪"),
            (75, 'milestone_75', "Amazing! You're 75% of the way! 🚀"),
            (100, 'milestone_100', 'Goal Achieved! Congratulations! 🎊'),
        ]
        
        for threshold, alert_type, message_prefix in milestones:
            if progress_percentage >= threshold:
                # Check if alert already triggered
                alert, created = GoalAlert.objects.get_or_create(
                    goal_id=goal_id,
                    user_id=user_id,
                    alert_type=alert_type,
                    defaults={'triggered': False}
                )
                
                if not alert.triggered:
                    # Trigger the alert
                    alert.trigger()
                    
                    # Send notifications
                    title = f"Savings Goal Milestone: {threshold}%"
                    message = f"{message_prefix} Keep up the great work!"
                    
                    results = NotificationService.send_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        category='goal_milestone',
                        notification_types=['email', 'push', 'dashboard'],
                        related_object_type='savings_goal',
                        related_object_id=goal_id,
                        user_email=user_email,
                    )
                    
                    # Link notifications to alert
                    for notification_log in results.values():
                        if isinstance(notification_log, NotificationLog):
                            alert.notification_logs.add(notification_log)
                    
                    logger.info(f"Milestone alert triggered for goal {goal_id}: {alert_type}")
    
    @staticmethod
    def check_deadline_alerts(goal_id: int, user_id: int, target_date, goal_name: str, user_email: str = None):
        """
        Check if goal deadline is approaching and send alerts.
        
        Args:
            goal_id: Savings goal ID
            user_id: User ID
            target_date: Target date for the goal
            goal_name: Name of the goal
            user_email: User's email address
        """
        if not target_date:
            return
        
        from datetime import timedelta
        today = timezone.now().date()
        days_remaining = (target_date - today).days
        
        deadline_alerts = [
            (7, 'deadline_week', f"1 week remaining to reach your goal: {goal_name}"),
            (1, 'deadline_day', f"Only 1 day left for your goal: {goal_name}!"),
            (-1, 'deadline_passed', f"Deadline passed for goal: {goal_name}"),
        ]
        
        for threshold, alert_type, message in deadline_alerts:
            should_trigger = (
                (threshold > 0 and days_remaining <= threshold and days_remaining > 0) or
                (threshold == -1 and days_remaining < 0)
            )
            
            if should_trigger:
                alert, created = GoalAlert.objects.get_or_create(
                    goal_id=goal_id,
                    user_id=user_id,
                    alert_type=alert_type,
                    defaults={'triggered': False}
                )
                
                if not alert.triggered:
                    alert.trigger()
                    
                    title = "Savings Goal Deadline Alert"
                    results = NotificationService.send_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        category='goal_deadline',
                        notification_types=['email', 'push', 'dashboard'],
                        related_object_type='savings_goal',
                        related_object_id=goal_id,
                        user_email=user_email,
                    )
                    
                    for notification_log in results.values():
                        if isinstance(notification_log, NotificationLog):
                            alert.notification_logs.add(notification_log)
                    
                    logger.info(f"Deadline alert triggered for goal {goal_id}: {alert_type}")
