from django.utils import timezone
from .models import AuditLog


def _get_ip_from_request(request):
    if not request:
        return None
    # Try common headers first (behind proxies)
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(user_id=None, action_type=None, resource_type=None, resource_id=None, metadata=None, request=None, user_agent=None):
    """Create an AuditLog entry. Call this from views/services when users perform actions.

    Example:
        from audit_logs.services import log_action
        log_action(user_id=current_user.id, action_type='CREATE', resource_type='expense', resource_id=str(exp.id), request=request)
    """
    if metadata is None:
        metadata = {}

    if user_agent is None and request is not None:
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    ip = _get_ip_from_request(request)

    # Create record (no strict validation here; model will enforce choices where used)
    AuditLog.objects.create(
        timestamp=timezone.now(),
        user_id=str(user_id) if user_id is not None else None,
        action_type=action_type or "",
        resource_type=resource_type or "",
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata=metadata,
        ip_address=ip,
        user_agent=user_agent,
    )
"""
Audit Logging Service
Provides centralized logging functionality for all user actions and system events.
"""
from .models import AuditLog


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_action(user_id, action_type, resource_type, resource_id=None, metadata=None, request=None):
    """
    Log an action to the audit log.
    
    Args:
        user_id: User ID performing the action (can be None for system events)
        action_type: Type of action (CREATE, READ, UPDATE, DELETE, LOGIN, etc.)
        resource_type: Type of resource affected (expense, goal, alert, reminder, user, etc.)
        resource_id: ID of the specific resource (optional)
        metadata: Additional context data as dictionary (optional)
        request: Django request object to extract IP and user agent (optional)
    
    Returns:
        AuditLog instance
    """
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    audit_log = AuditLog.objects.create(
        user_id=user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return audit_log


def log_create(user_id, resource_type, resource_id, metadata=None, request=None):
    """Log a CREATE action."""
    return log_action(user_id, 'CREATE', resource_type, resource_id, metadata, request)


def log_update(user_id, resource_type, resource_id, metadata=None, request=None):
    """Log an UPDATE action."""
    return log_action(user_id, 'UPDATE', resource_type, resource_id, metadata, request)


def log_delete(user_id, resource_type, resource_id, metadata=None, request=None):
    """Log a DELETE action."""
    return log_action(user_id, 'DELETE', resource_type, resource_id, metadata, request)


def log_login(user_id, success=True, metadata=None, request=None):
    """Log a login attempt."""
    action_type = 'LOGIN' if success else 'LOGIN_FAILED'
    return log_action(user_id, action_type, 'user', user_id, metadata, request)


def log_logout(user_id, metadata=None, request=None):
    """Log a logout."""
    return log_action(user_id, 'LOGOUT', 'user', user_id, metadata, request)


def log_access_denied(user_id, resource_type, resource_id=None, metadata=None, request=None):
    """Log an access denied event."""
    return log_action(user_id, 'ACCESS_DENIED', resource_type, resource_id, metadata, request)


def log_budget_breach(user_id, alert_id, metadata=None, request=None):
    """Log a budget threshold breach."""
    return log_action(user_id, 'BUDGET_BREACH', 'alert', alert_id, metadata, request)


def log_alert_triggered(user_id, alert_id, metadata=None, request=None):
    """Log an alert being triggered."""
    return log_action(user_id, 'ALERT_TRIGGERED', 'alert', alert_id, metadata, request)
