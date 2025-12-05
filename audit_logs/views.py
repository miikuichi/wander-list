from datetime import datetime, timedelta
import csv

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone

from login.decorators import require_authentication
from .models import AuditLog


# Human-friendly labels for each feature / resource_type
FEATURE_LABELS = {
    "expense": "Expenses",
    "goal": "Savings Goals",
    "alert": "Budget Alerts",
    "reminder": "Reminders",
    "user": "Account / Login",
    "monthly_allowance": "Monthly Allowance",
    "system": "System Events",
}


# =========================
# USER AUDIT LOG (existing)
# =========================
@require_authentication
def audit_logs_view(request):
    """
    Display audit logs for the current user with filtering options.
    (This is the user-facing audit log page.)
    """
    user_id = request.session.get("user_id")

    # Get filter parameters
    action_type = request.GET.get("action_type", "")
    resource_type = request.GET.get("resource_type", "")
    days_str = request.GET.get("days", "30")
    search = request.GET.get("search", "")

    try:
        days = int(days_str)
    except (TypeError, ValueError):
        days = 30

    # Base query = only this user's logs
    logs = AuditLog.objects.filter(user_id=user_id)

    # Date filter
    if days:
        start_date = datetime.now() - timedelta(days=days)
        logs = logs.filter(timestamp__gte=start_date)

    # Action filter
    if action_type:
        logs = logs.filter(action_type=action_type)

    # Resource filter
    if resource_type:
        logs = logs.filter(resource_type=resource_type)

    # Search filter
    if search:
        logs = logs.filter(
            Q(resource_id__icontains=search)
            | Q(ip_address__icontains=search)
        )

    # Stats for this user
    total_actions = logs.count()
    create_count = logs.filter(action_type="CREATE").count()
    update_count = logs.filter(action_type="UPDATE").count()
    delete_count = logs.filter(action_type="DELETE").count()
    login_count = logs.filter(action_type="LOGIN").count()
    failed_login_count = logs.filter(action_type="LOGIN_FAILED").count()

    # Limit to 100 most recent
    logs = logs.order_by("-timestamp")[:100]

    context = {
        "logs": logs,
        "total_actions": total_actions,
        "create_count": create_count,
        "update_count": update_count,
        "delete_count": delete_count,
        "login_count": login_count,
        "failed_login_count": failed_login_count,
        "action_types": AuditLog.ACTION_TYPES,
        "resource_types": AuditLog.RESOURCE_TYPES,
        "selected_action": action_type,
        "selected_resource": resource_type,
        "selected_days": days,
        "search_query": search,
    }

    return render(request, "audit_logs/audit_logs.html", context)


@require_authentication
def export_audit_logs(request):
    """
    Export *current user's* audit logs to CSV.
    Uses the same filters as audit_logs_view.
    """
    user_id = request.session.get("user_id")

    action_type = request.GET.get("action_type", "")
    resource_type = request.GET.get("resource_type", "")
    days_str = request.GET.get("days", "30")

    try:
        days = int(days_str)
    except (TypeError, ValueError):
        days = 30

    logs = AuditLog.objects.filter(user_id=user_id)

    if days:
        start_date = datetime.now() - timedelta(days=days)
        logs = logs.filter(timestamp__gte=start_date)

    if action_type:
        logs = logs.filter(action_type=action_type)

    if resource_type:
        logs = logs.filter(resource_type=resource_type)

    # CSV response
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Timestamp",
            "User ID",
            "Action Type",
            "Resource Type",
            "Resource ID",
            "IP Address",
            "User Agent",
            "Metadata",
        ]
    )

    for log in logs.order_by("-timestamp"):
        writer.writerow(
            [
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log.user_id or "",
                log.action_type,
                log.resource_type,
                log.resource_id or "",
                log.ip_address or "",
                log.user_agent or "",
                str(log.metadata),
            ]
        )

    return response


# ==================================
# ADMIN USAGE ANALYTICS (new / fixed)
# ==================================
@require_authentication
def admin_usage_analytics_view(request):
    """
    Admin usage analytics across ALL users.
    Shows totals and a breakdown of most-used features.
    """
    # Only allow admins
    if not request.session.get("is_admin"):
        return redirect("dashboard")

    # --- Filters from query string ---
    action_type = request.GET.get("action_type", "")
    resource_type = request.GET.get("resource_type", "")
    days = int(request.GET.get("days", 30) or 30)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Base queryset: ALL logs in date range (all users)
    logs = AuditLog.objects.filter(
        timestamp__gte=start_date, timestamp__lte=end_date
    )

    # Apply optional filters
    if action_type:
        logs = logs.filter(action_type=action_type)

    if resource_type:
        logs = logs.filter(resource_type=resource_type)

    # ====== Overview metrics (use ALL logs) ======
    total_actions = logs.count()
    login_count = logs.filter(action_type="LOGIN").count()
    created_count = logs.filter(action_type="CREATE").count()
    updated_count = logs.filter(action_type="UPDATE").count()

    # ====== Most used features (exclude auth noise) ======
    feature_logs = logs.exclude(
        action_type__in=["LOGIN", "LOGOUT", "LOGIN_FAILED"]
    ).exclude(resource_type="user")

    # Group by resource_type and count
    top_features_qs = (
        feature_logs.values("resource_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    # Nice labels for the resource types
    FEATURE_LABELS = {
        "expense": "Expenses",
        "goal": "Savings Goals",
        "alert": "Budget Alerts",
        "reminder": "Reminders",
        "monthly_allowance": "Monthly Allowance",
        "system": "System",
        "user": "Profile / Account",
    }

    top_features = [
        {
            "name": FEATURE_LABELS.get(row["resource_type"], row["resource_type"]),
            "code": row["resource_type"],
            "count": row["count"],
        }
        for row in top_features_qs
    ]

    # ====== Recent activity (still ALL logs with filters) ======
    recent_logs = logs.order_by("-timestamp")[:100]

    context = {
        "logs": recent_logs,
        "total_actions": total_actions,
        "login_count": login_count,
        "create_count": created_count,
        "update_count": updated_count,
        # we’re not tracking delete explicitly in cards now, only if you want:
        "delete_count": logs.filter(action_type="DELETE").count(),

        "top_features": top_features,

        # Filters
        "action_types": AuditLog.ACTION_TYPES,
        "resource_types": AuditLog.RESOURCE_TYPES,
        "selected_action": action_type,
        "selected_resource": resource_type,
        "selected_days": days,
    }

    return render(request, "admin_analytics/admin_analytics.html", context)

@require_authentication
def admin_usage_export_csv(request):
    """
    Export filtered admin usage analytics (ALL users) to CSV.
    """
    if not request.session.get("is_admin"):
        return redirect("dashboard")

    action_type = request.GET.get("action_type", "")
    resource_type = request.GET.get("resource_type", "")
    days = int(request.GET.get("days", 30) or 30)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    logs = AuditLog.objects.filter(
        timestamp__gte=start_date, timestamp__lte=end_date
    )

    if action_type:
        logs = logs.filter(action_type=action_type)

    if resource_type:
        logs = logs.filter(resource_type=resource_type)

    filename = f"usage_analytics_{start_date.date()}_to_{end_date.date()}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Timestamp",
        "User ID",
        "Action Type",
        "Resource Type",
        "Resource ID",
        "IP Address",
        "User Agent",
        "Metadata",
    ])

    for log in logs.order_by("-timestamp"):
        writer.writerow([
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.user_id or "",
            log.action_type,
            log.resource_type,
            log.resource_id or "",
            log.ip_address or "",
            (log.user_agent or "")[:250],  # avoid insane length
            str(log.metadata or ""),
        ])

    return response

