from django import forms
from .models import SavingsGoal, SavingsTransaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SavingsGoalForm(forms.ModelForm):
    """Form for creating and editing savings goals."""
    
    class Meta:
        model = SavingsGoal
        fields = ['name', 'target_amount', 'description', 'target_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., New Laptop, Emergency Fund',
                'required': True
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Add details about your goal...',
                'rows': 3
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'name': 'Goal Name',
            'target_amount': 'Target Amount (₱)',
            'description': 'Description',
            'target_date': 'Target Date (Optional)',
        }
    
    def clean_target_amount(self):
        """Validate target amount."""
        try:
            amount = self.cleaned_data.get('target_amount')
            
            if amount is None:
                raise forms.ValidationError("Target amount is required.")
            
            if amount <= 0:
                raise forms.ValidationError("Target amount must be greater than zero.")
            
            if amount > Decimal('999999999.99'):
                raise forms.ValidationError("Target amount is too large. Maximum is ₱999,999,999.99")
            
            return amount
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating target amount: {e}")
            raise forms.ValidationError("Please enter a valid amount.")
    
    def clean_name(self):
        """Validate and clean goal name."""
        try:
            name = self.cleaned_data.get('name', '').strip()
            
            if not name:
                raise forms.ValidationError("Goal name is required.")
            
            if len(name) < 3:
                raise forms.ValidationError("Goal name must be at least 3 characters long.")
            
            if len(name) > 100:
                raise forms.ValidationError("Goal name must be 100 characters or less.")
            
            return name
        except Exception as e:
            logger.error(f"Error validating goal name: {e}")
            raise


class AddSavingsForm(forms.Form):
    """Form for adding savings to a goal."""
    
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01',
            'required': True
        }),
        label='Amount to Add (₱)'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Add a note about this contribution...',
            'rows': 2
        }),
        label='Notes (Optional)'
    )
    
    def clean_amount(self):
        """Validate amount."""
        try:
            amount = self.cleaned_data.get('amount')
            
            if amount is None:
                raise forms.ValidationError("Amount is required.")
            
            if amount <= 0:
                raise forms.ValidationError("Amount must be greater than zero.")
            
            if amount > Decimal('999999999.99'):
                raise forms.ValidationError("Amount is too large. Maximum is ₱999,999,999.99")
            
            return amount
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating savings amount: {e}")
            raise forms.ValidationError("Please enter a valid amount.")
