from django.contrib import admin
from .models import Category, BudgetAlert, BudgetHistory, AlertHistory

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    search_fields = ("name", "user__username")

@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ("category", "amount_limit", "threshold_percent", "active", "user", "is_snoozed", "created_at")
    list_filter = ("active", "threshold_percent", "threshold_50", "threshold_75", "threshold_90", "threshold_100")
    search_fields = ("category__name", "user__username")
    readonly_fields = ("created_at", "updated_at")
    
    def is_snoozed(self, obj):
        return obj.is_snoozed()
    is_snoozed.boolean = True
    is_snoozed.short_description = "Snoozed"

@admin.register(BudgetHistory)
class BudgetHistoryAdmin(admin.ModelAdmin):
    list_display = ("category", "user_id", "amount_limit", "previous_limit", "change_date")
    list_filter = ("change_date", "category")
    search_fields = ("user_id", "category")
    readonly_fields = ("change_date",)
    ordering = ("-change_date",)

@admin.register(AlertHistory)
class AlertHistoryAdmin(admin.ModelAdmin):
    list_display = ("category", "user_id", "threshold_level", "severity", "usage_percent", "triggered_at", "acknowledged")
    list_filter = ("severity", "threshold_level", "acknowledged", "triggered_at")
    search_fields = ("user_id", "category")
    readonly_fields = ("triggered_at",)
    ordering = ("-triggered_at",)
