"""
Security decorators for access control and authorization.

These decorators ensure users can only access their own data and prevent
unauthorized access through endpoint manipulation.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
import logging

logger = logging.getLogger(__name__)


def require_authentication(view_func):
    """
    Decorator to ensure user is authenticated before accessing a view.
    Redirects to login page if not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            logger.warning(f"Unauthenticated access attempt to {view_func.__name__}")
            messages.warning(request, "⚠️ Please log in to access this page.")
            return redirect('login:login_page')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_owner(resource_type='resource', id_param='id', user_id_field='user_id'):
    """
    Decorator to verify user owns the resource they're trying to access.
    
    Args:
        resource_type: Name of resource for error messages (e.g., 'expense', 'goal')
        id_param: Name of URL parameter containing resource ID
        user_id_field: Name of field in database table containing user_id
    
    Usage:
        @require_owner(resource_type='expense', id_param='expense_id')
        def delete_expense_view(request, expense_id):
            # User ownership already verified
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check authentication first
            session_user_id = request.session.get('user_id')
            if not session_user_id:
                logger.warning(
                    f"Unauthenticated access attempt to {view_func.__name__}"
                )
                messages.warning(request, "⚠️ Please log in to access this page.")
                return redirect('login:login_page')
            
            # Get resource ID from kwargs
            resource_id = kwargs.get(id_param)
            
            # If no resource ID, just check authentication
            if resource_id is None:
                return view_func(request, *args, **kwargs)
            
            # Import here to avoid circular imports
            from supabase_service import get_service_client
            
            # Determine table name from resource type
            table_mapping = {
                'expense': 'expenses',
                'goal': 'savings_goals',
                'alert': 'budget_alerts',
                'reminder': 'reminders',
                'notification': 'notification_logs',
            }
            
            table_name = table_mapping.get(resource_type, resource_type + 's')
            
            try:
                # Query database to verify ownership
                supabase = get_service_client()
                response = supabase.table(table_name)\
                    .select('id, ' + user_id_field)\
                    .eq('id', resource_id)\
                    .execute()
                
                if not response.data:
                    logger.warning(
                        f"Access denied: {resource_type} {resource_id} not found "
                        f"for user {session_user_id}"
                    )
                    messages.error(
                        request,
                        f"⚠️ {resource_type.capitalize()} not found or you don't have permission to access it."
                    )
                    # Return appropriate response based on request type
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse(
                            {'error': 'Access denied'}, 
                            status=403
                        )
                    return HttpResponseForbidden(
                        f"You don't have permission to access this {resource_type}."
                    )
                
                # Verify user owns this resource
                resource = response.data[0]
                resource_user_id = resource.get(user_id_field)
                
                if resource_user_id != session_user_id:
                    logger.error(
                        f"SECURITY ALERT: User {session_user_id} attempted to access "
                        f"{resource_type} {resource_id} owned by user {resource_user_id}"
                    )
                    messages.error(
                        request,
                        f"⚠️ Access denied. You don't have permission to access this {resource_type}."
                    )
                    # Return appropriate response based on request type
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse(
                            {'error': 'Access denied'}, 
                            status=403
                        )
                    return HttpResponseForbidden(
                        f"You don't have permission to access this {resource_type}."
                    )
                
                # User verified - proceed with view
                logger.info(
                    f"Access granted: user {session_user_id} accessing "
                    f"{resource_type} {resource_id}"
                )
                return view_func(request, *args, **kwargs)
                
            except Exception as e:
                logger.error(
                    f"Error verifying ownership for {resource_type} {resource_id}: {e}",
                    exc_info=True
                )
                messages.error(
                    request,
                    f"⚠️ An error occurred while verifying access permissions."
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(
                        {'error': 'Server error'}, 
                        status=500
                    )
                return redirect('dashboard')
        
        return wrapper
    return decorator


def require_json_authentication(view_func):
    """
    Decorator for JSON API endpoints that require authentication.
    Returns JSON error instead of redirecting.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            logger.warning(
                f"Unauthenticated API access attempt to {view_func.__name__}"
            )
            return JsonResponse(
                {'error': 'Authentication required'},
                status=401
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def rate_limit(max_attempts=5, window_seconds=300):
    """
    Simple rate limiting decorator to prevent brute force attacks.
    
    Args:
        max_attempts: Maximum number of attempts allowed
        window_seconds: Time window in seconds
    
    Usage:
        @rate_limit(max_attempts=5, window_seconds=300)
        def login_view(request):
            ...
    """
    def decorator(view_func):
        # Store attempt counts in memory (use Redis/Memcached in production)
        attempts = {}
        
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Check attempts
            from time import time
            current_time = time()
            
            if ip in attempts:
                attempt_list = attempts[ip]
                # Remove old attempts outside window
                attempt_list = [t for t in attempt_list if current_time - t < window_seconds]
                
                if len(attempt_list) >= max_attempts:
                    logger.warning(
                        f"Rate limit exceeded for IP {ip} on {view_func.__name__}"
                    )
                    messages.error(
                        request,
                        f"⚠️ Too many attempts. Please try again in {window_seconds // 60} minutes."
                    )
                    return redirect('login:login_page')
                
                attempts[ip] = attempt_list + [current_time]
            else:
                attempts[ip] = [current_time]
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
