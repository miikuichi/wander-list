from django.contrib import admin
from .models import SavingsGoal, SavingsTransaction


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_id', 'current_amount', 'target_amount', 'progress_percentage', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'user_id', 'description']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'progress_percentage', 'remaining_amount', 'is_complete']
    
    fieldsets = (
        ('Goal Information', {
            'fields': ('user_id', 'name', 'description')
        }),
        ('Financial Details', {
            'fields': ('target_amount', 'current_amount', 'target_date')
        }),
        ('Status', {
            'fields': ('status', 'progress_percentage', 'remaining_amount', 'is_complete')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ['goal', 'transaction_type', 'amount', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['goal__name', 'notes']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('goal', 'transaction_type', 'amount', 'notes')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
        }),
    )
