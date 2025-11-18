from django.contrib import admin
from .models import NotificationLog, UserNotificationPreference, GoalAlert


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['title', 'user_id', 'notification_type', 'category', 'status', 'created_at']
    list_filter = ['notification_type', 'category', 'status', 'created_at']
    search_fields = ['title', 'message', 'user_id']
    readonly_fields = ['created_at', 'sent_at', 'read_at']
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('user_id', 'notification_type', 'category', 'title', 'message')
        }),
        ('Related Object', {
            'fields': ('related_object_type', 'related_object_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at', 'read_at')
        }),
    )


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'email_enabled', 'push_enabled', 'updated_at']
    list_filter = ['email_enabled', 'push_enabled']
    search_fields = ['user_id']
    
    fieldsets = (
        ('User', {
            'fields': ('user_id',)
        }),
        ('Email Preferences', {
            'fields': ('email_enabled', 'email_budget_alerts', 'email_goal_milestones', 
                      'email_goal_deadlines', 'email_reminders')
        }),
        ('Push Preferences', {
            'fields': ('push_enabled', 'push_budget_alerts', 'push_goal_milestones',
                      'push_goal_deadlines', 'push_reminders', 'fcm_token')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GoalAlert)
class GoalAlertAdmin(admin.ModelAdmin):
    list_display = ['goal_id', 'user_id', 'alert_type', 'triggered', 'triggered_at']
    list_filter = ['alert_type', 'triggered', 'created_at']
    search_fields = ['goal_id', 'user_id']
    readonly_fields = ['created_at', 'triggered_at']
    filter_horizontal = ['notification_logs']
