"""
Django management command to test email notifications.

Usage:
    python manage.py test_email
    python manage.py test_email --email your-email@example.com
    python manage.py test_email --all-categories
"""
from django.core.management.base import BaseCommand
from notifications.services import NotificationService
from notifications.models import NotificationLog
from login.models import User


class Command(BaseCommand):
    help = 'Send test email notifications to verify email setup is working'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send test notification to (default: michaelsevilla0927@gmail.com)',
            default='michaelsevilla0927@gmail.com'
        )
        parser.add_argument(
            '--all-categories',
            action='store_true',
            help='Send test emails for all notification categories'
        )

    def handle(self, *args, **options):
        email = options['email']
        send_all = options['all_categories']
        
        self.stdout.write(self.style.WARNING('🚀 Testing Email Notification System...'))
        self.stdout.write(f'📧 Sending to: {email}\n')
        
        # Try to get the user from the database
        try:
            user = User.objects.filter(email=email).first()
            if user:
                user_id = user.id
                self.stdout.write(self.style.SUCCESS(f'✓ Found user: {user.username} (ID: {user_id})'))
            else:
                # Use default user ID 1 if no user found
                user_id = 1
                self.stdout.write(self.style.WARNING(f'⚠ No user found with email {email}, using user_id=1'))
        except Exception as e:
            user_id = 1
            self.stdout.write(self.style.WARNING(f'⚠ Error finding user: {e}, using user_id=1'))
        
        if send_all:
            # Send test for all categories
            categories = [
                ('budget_alert', 'Budget Alert Test', 'You have spent 85% of your monthly budget for Food category.'),
                ('goal_milestone', 'Savings Goal Milestone', 'Congratulations! You have reached 50% of your goal "Emergency Fund"!'),
                ('goal_deadline', 'Goal Deadline Warning', 'Your savings goal "Vacation Fund" is due in 7 days. Current progress: 60%'),
                ('goal_achieved', 'Goal Achieved!', '🎉 Congratulations! You have achieved your savings goal "New Laptop"!'),
                ('reminder', 'Expense Reminder', 'Remember to log your daily expenses to stay on track with your budget.'),
                ('expense', 'Large Expense Alert', 'You just recorded a large expense of ₱5,000 for Shopping.'),
            ]
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write('Sending test emails for all categories...\n')
            
            success_count = 0
            failed_count = 0
            
            for category, title, message in categories:
                try:
                    result = NotificationService.send_notification(
                        user_id=user_id,
                        title=title,
                        message=message,
                        category=category,
                        notification_types=['email', 'dashboard'],
                        user_email=email
                    )
                    
                    if result.get('email'):
                        log = result['email']
                        if log.status == 'sent':
                            self.stdout.write(self.style.SUCCESS(f'✓ {category}: {title}'))
                            success_count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f'✗ {category}: Failed - {log.error_message}'))
                            failed_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'⚠ {category}: No email result'))
                        failed_count += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ {category}: Error - {str(e)}'))
                    failed_count += 1
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(f'Results: {success_count} sent, {failed_count} failed')
            
        else:
            # Send single test email
            self.stdout.write('\nSending test email...')
            
            try:
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
                    user_email=email
                )
                
                if result.get('email'):
                    log = result['email']
                    if log.status == 'sent':
                        self.stdout.write(self.style.SUCCESS('\n✓ Email sent successfully!'))
                        self.stdout.write(f'  Notification ID: {log.id}')
                        self.stdout.write(f'  Status: {log.status}')
                        self.stdout.write(f'  Sent at: {log.sent_at}')
                        self.stdout.write('\n📧 Check your inbox at: ' + email)
                        self.stdout.write('   (Check spam folder if you don\'t see it)')
                    else:
                        self.stdout.write(self.style.ERROR(f'\n✗ Email failed to send'))
                        self.stdout.write(f'  Error: {log.error_message}')
                        self.stdout.write('\nTroubleshooting:')
                        self.stdout.write('  1. Check your .env file has correct EMAIL_HOST_USER and EMAIL_HOST_PASSWORD')
                        self.stdout.write('  2. Verify Gmail App Password is correct (16 characters)')
                        self.stdout.write('  3. Check settings.py has EMAIL_BACKEND = \'django.core.mail.backends.smtp.EmailBackend\'')
                else:
                    self.stdout.write(self.style.WARNING('\n⚠ No email result returned'))
                    
                # Show dashboard notification status
                if result.get('dashboard'):
                    dashboard_log = result['dashboard']
                    self.stdout.write(self.style.SUCCESS(f'\n✓ Dashboard notification created (ID: {dashboard_log.id})'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n✗ Error sending email: {str(e)}'))
                import traceback
                self.stdout.write(traceback.format_exc())
        
        # Show recent notifications
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Recent Email Notifications:')
        recent = NotificationLog.objects.filter(
            notification_type='email'
        ).order_by('-created_at')[:5]
        
        if recent.exists():
            for log in recent:
                status_icon = '✓' if log.status == 'sent' else '✗'
                self.stdout.write(f'  {status_icon} {log.title} - {log.status} ({log.created_at.strftime("%H:%M:%S")})')
        else:
            self.stdout.write('  No email notifications found in database')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ Test complete!'))
