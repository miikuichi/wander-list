from django.contrib import admin
from .models import Category, BudgetAlert

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    search_fields = ("name", "user__username")

@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ("category", "amount_limit", "threshold_percent", "active", "user", "created_at")
    list_filter = ("active", "threshold_percent")
    search_fields = ("category__name", "user__username")
