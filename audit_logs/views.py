from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from login.decorators import require_authentication
import csv
from datetime import datetime, timedelta
from .models import AuditLog


@require_authentication
def audit_logs_view(request):
    """
    Display audit logs for the current user with filtering options.
    """
    user_id = request.session.get('user_id')
    
    # Get filter parameters
    action_type = request.GET.get('action_type', '')
    resource_type = request.GET.get('resource_type', '')
    days = int(request.GET.get('days', 30))
    search = request.GET.get('search', '')
    
    # Build query
    logs = AuditLog.objects.filter(user_id=user_id)
    
    # Apply date filter
    if days:
        start_date = datetime.now() - timedelta(days=days)
        logs = logs.filter(timestamp__gte=start_date)
    
    # Apply action type filter
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    # Apply resource type filter
    if resource_type:
        logs = logs.filter(resource_type=resource_type)
    
    # Apply search filter
    if search:
        logs = logs.filter(
            Q(resource_id__icontains=search) |
            Q(ip_address__icontains=search)
        )
    
    # Get statistics
    total_actions = logs.count()
    create_count = logs.filter(action_type='CREATE').count()
    update_count = logs.filter(action_type='UPDATE').count()
    delete_count = logs.filter(action_type='DELETE').count()
    login_count = logs.filter(action_type='LOGIN').count()
    failed_login_count = logs.filter(action_type='LOGIN_FAILED').count()
    
    # Paginate (limit to 100 most recent)
    logs = logs[:100]
    
    context = {
        'logs': logs,
        'total_actions': total_actions,
        'create_count': create_count,
        'update_count': update_count,
        'delete_count': delete_count,
        'login_count': login_count,
        'failed_login_count': failed_login_count,
        'action_types': AuditLog.ACTION_TYPES,
        'resource_types': AuditLog.RESOURCE_TYPES,
        'selected_action': action_type,
        'selected_resource': resource_type,
        'selected_days': days,
        'search_query': search,
    }
    
    return render(request, 'audit_logs/audit_logs.html', context)


@require_authentication
def export_audit_logs(request):
    """
    Export audit logs to CSV file.
    """
    user_id = request.session.get('user_id')
    
    # Get filter parameters (same as view)
    action_type = request.GET.get('action_type', '')
    resource_type = request.GET.get('resource_type', '')
    days = int(request.GET.get('days', 30))
    
    # Build query
    logs = AuditLog.objects.filter(user_id=user_id)
    
    if days:
        start_date = datetime.now() - timedelta(days=days)
        logs = logs.filter(timestamp__gte=start_date)
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    if resource_type:
        logs = logs.filter(resource_type=resource_type)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Action Type', 'Resource Type', 'Resource ID', 'IP Address', 'User Agent', 'Metadata'])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.action_type,
            log.resource_type,
            log.resource_id or '',
            log.ip_address or '',
            log.user_agent or '',
            str(log.metadata)
        ])
    
    return response
