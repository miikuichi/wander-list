from django import forms
from .models import BudgetAlert

class BudgetAlertForm(forms.ModelForm):
    class Meta:
        model = BudgetAlert
        fields = (
            "amount_limit", "category", "threshold_percent",
            "notify_dashboard", "notify_email", "notify_push", "active"
        )
        widgets = {
            "threshold_percent": forms.NumberInput(attrs={"type": "range", "min": 10, "max": 100, "step": 5}),
        }

    def clean_amount_limit(self):
        v = self.cleaned_data.get("amount_limit")
        if not v or v <= 0:
            raise forms.ValidationError("Amount is required.")
        return v

    def clean_category(self):
        v = self.cleaned_data.get("category")
        if not v:
            raise forms.ValidationError("Category is required.")
        return v
