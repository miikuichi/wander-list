from django import forms
from .models import BudgetAlert
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Hardcoded major categories as requested
MAJOR_CATEGORIES = [
    'Food',
    'Transport', 
    'Leisure',
    'Bills',
    'School Supplies',
    'Shopping',
    'Healthcare',
    'Entertainment',
]

class BudgetAlertForm(forms.Form):
    """
    Enhanced Budget Alert Form with:
    - Hardcoded major categories
    - "Others" option with custom text input
    - Category name similarity detection
    - Duplicate category prevention
    """
    
    # Category selection with "Others" option
    category_choice = forms.ChoiceField(
        label="Category",
        choices=[],  # Will be populated in __init__
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_category_choice',
            'onchange': 'toggleCustomCategory()'
        }),
        required=True
    )
    
    # Custom category name (shown only when "Others" is selected)
    custom_category = forms.CharField(
        label="Custom Category Name",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_custom_category',
            'placeholder': 'Enter custom category name...',
            'style': 'display: none;'
        })
    )
    
    amount_limit = forms.DecimalField(
        label="Budget Limit (₱)",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1000.00',
            'step': '0.01'
        })
    )
    
    threshold_percent = forms.IntegerField(
        label="Alert Threshold (%)",
        min_value=10,
        max_value=100,
        initial=80,
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'class': 'form-range',
            'min': '10',
            'max': '100',
            'step': '5',
            'oninput': 'updateThresholdValue(this.value)'
        })
    )
    
    notify_dashboard = forms.BooleanField(
        label="Notification Bell",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notify_email = forms.BooleanField(
        label="Email Notification",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notify_push = forms.BooleanField(
        label="Push Notification",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    active = forms.BooleanField(
        label="Active",
        required=False,
        initial=True,
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        
        # Build category choices: major categories + "Others"
        category_choices = [(cat, cat) for cat in MAJOR_CATEGORIES]
        category_choices.append(('Others', 'Others (Custom)'))
        self.fields['category_choice'].choices = category_choices
        
        # If editing existing alert, set initial values
        if self.instance:
            self.fields['amount_limit'].initial = self.instance.amount_limit
            self.fields['threshold_percent'].initial = self.instance.threshold_percent
            self.fields['notify_dashboard'].initial = self.instance.notify_dashboard
            self.fields['notify_email'].initial = self.instance.notify_email
            self.fields['notify_push'].initial = self.instance.notify_push
            self.fields['active'].initial = self.instance.active
            
            # Set category
            category_name = self.instance.category.name
            if category_name in MAJOR_CATEGORIES:
                self.fields['category_choice'].initial = category_name
            else:
                self.fields['category_choice'].initial = 'Others'
                self.fields['custom_category'].initial = category_name

    def normalize_category_name(self, input_name):
        """
        Normalizes category name to match predefined categories.
        Returns the standard name if similar, otherwise returns input.
        """
        input_lower = input_name.lower().strip()
        
        # Check for exact or partial matches
        for major_cat in MAJOR_CATEGORIES:
            major_lower = major_cat.lower()
            
            # Exact match
            if input_lower == major_lower:
                return major_cat
            
            # Input contains major category
            if major_lower in input_lower:
                return major_cat
            
            # Major category contains input
            if input_lower in major_lower:
                return major_cat
        
        # No match, return original (capitalized)
        return input_name.strip().title()

    def clean(self):
        cleaned_data = super().clean()
        category_choice = cleaned_data.get('category_choice')
        custom_category = cleaned_data.get('custom_category')
        amount_limit = cleaned_data.get('amount_limit')
        
        try:
            # Determine final category name
            if category_choice == 'Others':
                if not custom_category:
                    raise forms.ValidationError({
                        'custom_category': 'Please enter a custom category name when "Others" is selected.'
                    })
                
                # Normalize the custom category name
                final_category = self.normalize_category_name(custom_category)
                
                # Log if normalization changed the name
                if final_category != custom_category.strip():
                    logger.info(f"Normalized category '{custom_category}' to '{final_category}'")
                
                cleaned_data['final_category_name'] = final_category
            else:
                cleaned_data['final_category_name'] = category_choice
            
            # Check for duplicate category (same category already has a budget alert)
            if self.user:
                from supabase_service import get_service_client
                
                try:
                    supabase = get_service_client()
                    
                    # Check if there's already an active budget alert for this category (SIMPLIFIED)
                    existing_alert = supabase.table('budget_alerts')\
                        .select('id, amount_limit, threshold_percent')\
                        .eq('user_id', self.user)\
                        .eq('category', cleaned_data['final_category_name'])\
                        .eq('active', True)\
                        .execute()
                    
                    if existing_alert.data:
                        # If editing, check if it's a different alert
                        if self.instance and hasattr(self.instance, 'id'):
                            # Editing mode - check if it's the same alert
                            if existing_alert.data[0]['id'] == self.instance.id:
                                # It's the same alert being edited, allow it
                                pass
                            else:
                                # Different alert exists
                                alert_data = existing_alert.data[0]
                                raise forms.ValidationError({
                                    'category_choice': f'⚠️ A budget alert already exists for "{cleaned_data["final_category_name"]}" '
                                                     f'(₱{alert_data["amount_limit"]}, {alert_data["threshold_percent"]}% threshold). '
                                                     f'Please edit or delete the existing alert first.'
                                })
                        elif not self.instance:
                            # Creating new alert - duplicate not allowed
                            alert_data = existing_alert.data[0]
                            raise forms.ValidationError({
                                'category_choice': f'⚠️ A budget alert already exists for "{cleaned_data["final_category_name"]}" '
                                                 f'(₱{alert_data["amount_limit"]}, {alert_data["threshold_percent"]}% threshold). '
                                                 f'Please edit or delete the existing alert first.'
                            })
                except Exception as e:
                    if isinstance(e, forms.ValidationError):
                        raise
                    logger.error(f"Error checking duplicate category: {e}", exc_info=True)
            
            # Validate amount limit
            if amount_limit and amount_limit > Decimal('999999999.99'):
                raise forms.ValidationError({
                    'amount_limit': '⚠️ Budget limit is too large. Maximum is ₱999,999,999.99'
                })
            
            logger.info(f"Form validation passed: category={cleaned_data['final_category_name']}, "
                       f"amount={amount_limit}")
            
        except forms.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error in form validation: {e}", exc_info=True)
            raise forms.ValidationError("⚠️ An error occurred during validation. Please try again.")
        
        return cleaned_data

    def clean_amount_limit(self):
        v = self.cleaned_data.get("amount_limit")
        if not v or v <= 0:
            raise forms.ValidationError("⚠️ Budget limit must be greater than zero.")
        if v > Decimal('999999999.99'):
            raise forms.ValidationError("⚠️ Budget limit is too large. Maximum is ₱999,999,999.99")
        return v

    def clean_threshold_percent(self):
        v = self.cleaned_data.get("threshold_percent")
        if v is None or v < 10 or v > 100:
            raise forms.ValidationError("⚠️ Threshold must be between 10% and 100%.")
        return v
