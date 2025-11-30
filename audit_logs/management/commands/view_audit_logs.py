from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from audit_logs.models import AuditLog
from tabulate import tabulate


class Command(BaseCommand):
    help = 'View and filter audit logs from the command line'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by user ID',
        )
        parser.add_argument(
            '--action',
            type=str,
            choices=['CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'ACCESS_DENIED', 'BUDGET_BREACH', 'ALERT_TRIGGERED'],
            help='Filter by action type',
        )
        parser.add_argument(
            '--resource',
            type=str,
            choices=['expense', 'goal', 'alert', 'reminder', 'user', 'monthly_allowance', 'system'],
            help='Filter by resource type',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back (default: 7)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of logs to display (default: 50)',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Export logs to CSV file (provide filename)',
        )

    def handle(self, *args, **options):
        # Build query
        logs = AuditLog.objects.all()
        
        # Apply filters
        if options['user']:
            logs = logs.filter(user_id=options['user'])
            self.stdout.write(f"Filtering by user: {options['user']}")
        
        if options['action']:
            logs = logs.filter(action_type=options['action'])
            self.stdout.write(f"Filtering by action: {options['action']}")
        
        if options['resource']:
            logs = logs.filter(resource_type=options['resource'])
            self.stdout.write(f"Filtering by resource: {options['resource']}")
        
        # Apply date filter
        if options['days']:
            start_date = timezone.now() - timedelta(days=options['days'])
            logs = logs.filter(timestamp__gte=start_date)
            self.stdout.write(f"Showing logs from last {options['days']} days")
        
        # Get count before limiting
        total_count = logs.count()
        
        # Apply limit
        logs = logs[:options['limit']]
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No audit logs found matching criteria.'))
            return
        
        # Export to CSV if requested
        if options['export']:
            self.export_to_csv(logs, options['export'])
            self.stdout.write(self.style.SUCCESS(f'Exported {len(logs)} logs to {options["export"]}'))
            return
        
        # Display statistics
        self.stdout.write(self.style.SUCCESS(f'\nFound {total_count} logs (showing {len(logs)})'))
        
        # Display logs in table format
        table_data = []
        for log in logs:
            table_data.append([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user_id or 'N/A',
                log.action_type,
                log.resource_type,
                log.resource_id or 'N/A',
                log.ip_address or 'N/A',
            ])
        
        headers = ['Timestamp', 'User ID', 'Action', 'Resource', 'Resource ID', 'IP Address']
        self.stdout.write('\n' + tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Display action type breakdown
        self.stdout.write('\n' + self.style.SUCCESS('Action Type Breakdown:'))
        action_counts = {}
        for action_type, _ in AuditLog.ACTION_TYPES:
            count = AuditLog.objects.filter(action_type=action_type).count()
            if count > 0:
                action_counts[action_type] = count
        
        for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"  {action}: {count}")
    
    def export_to_csv(self, logs, filename):
        """Export logs to CSV file."""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'User ID', 'Action Type', 'Resource Type', 'Resource ID', 'IP Address', 'User Agent', 'Metadata'])
            
            for log in logs:
                writer.writerow([
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    log.user_id or '',
                    log.action_type,
                    log.resource_type,
                    log.resource_id or '',
                    log.ip_address or '',
                    log.user_agent or '',
                    str(log.metadata)
                ])
