from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Sum
from .models import Expense, Category
from budget_alerts.models import BudgetAlert # 💡 FIX 1: Import BudgetAlert instead of Budget

class ExpenseForm(forms.ModelForm):
    # Overriding the category field to ensure the user only sees their own categories later
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        empty_label="Select a category",
        widget=forms.Select(attrs={'class': 'form-select', 'required': True})
    )

    class Meta:
        model = Expense
        fields = ['amount', 'category', 'date', 'notes']
        
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '50.00', 'step': '0.01', 'required': True}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'e.g., Lunch with friends...', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)

        if self.user and self.user.is_authenticated:
            # Assuming the user model has a reverse relation named 'expense_categories'
            self.fields['category'].queryset = self.user.expense_categories.all()

    def clean(self):
        """
        Performs custom validation, now checking against the CATEGORY-SPECIFIC BudgetAlert.
        """
        cleaned_data = super().clean()
        expense_amount = cleaned_data.get("amount") 
        expense_category = cleaned_data.get("category") # Get the selected Category object
        
        if expense_amount is not None and expense_category is not None and self.user and self.user.is_authenticated:
            
            # --- 2. CATEGORY-SPECIFIC BUDGET ALERT CHECK ---
            
            budget_alert = None
            # The BudgetAlert model references a Category model in the budget_alerts app.
            # The expenses app has its own Category model (different class), so we must
            # not pass an expenses.Category instance into a query expecting a
            # budget_alerts.Category instance. Instead, look up alerts by category name.
            try:
                budget_alert = BudgetAlert.objects.filter(
                    user=self.user,
                    category__name=expense_category.name,
                    active=True
                ).first()
                amount_limit = budget_alert.amount_limit if budget_alert else None
            except Exception:
                # Safe fallback: no alert found or unexpected error
                amount_limit = None

            if amount_limit is not None:
                # Calculate current spending for THIS CATEGORY
                expenses_query = Expense.objects.filter(user=self.user, category=expense_category)
                
                # If editing, exclude its current amount
                if self.instance and self.instance.pk:
                     expenses_query = expenses_query.exclude(pk=self.instance.pk)

                # Sum up all existing expenses for THIS CATEGORY
                current_total_category_expenses = expenses_query.aggregate(Sum('amount'))['amount__sum'] or 0
                
                # Calculate the total spending if the proposed expense is added
                proposed_total = current_total_category_expenses + expense_amount
                
                # The part that 'complains' if the category limit is exceeded
                if proposed_total > amount_limit:
                    remaining_limit = amount_limit - current_total_category_expenses
                    
                    # Use self.add_error() to raise a validation error tied to the 'amount' field
                    self.add_error(
                        'amount',  
                        (f"🛑 Category Limit Alert! This expense (${expense_amount:.2f}) exceeds the limit set for '{expense_category.name}'. "
                         f"You only have ${remaining_limit:.2f} remaining out of your total ${amount_limit:.2f} limit for this category.")
                    )

        return cleaned_data
