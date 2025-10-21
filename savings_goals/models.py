from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SavingsGoal(models.Model):
    """Model for tracking user savings goals with progress and status."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    # Link to user via user_id (stored in session, not Django auth)
    user_id = models.BigIntegerField(db_index=True)
    
    # Goal details
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Target amount to save"
    )
    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current saved amount"
    )
    
    # Optional fields
    description = models.TextField(blank=True, null=True)
    target_date = models.DateField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['user_id', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - ₱{self.current_amount}/₱{self.target_amount}"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage."""
        try:
            if self.target_amount > 0:
                percentage = (self.current_amount / self.target_amount) * 100
                return min(round(percentage, 2), 100)  # Cap at 100%
            return 0
        except Exception as e:
            logger.error(f"Error calculating progress percentage for goal {self.id}: {e}")
            return 0
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to reach goal."""
        try:
            remaining = self.target_amount - self.current_amount
            return max(remaining, Decimal('0.00'))  # Don't return negative
        except Exception as e:
            logger.error(f"Error calculating remaining amount for goal {self.id}: {e}")
            return Decimal('0.00')
    
    @property
    def is_complete(self):
        """Check if goal is complete."""
        try:
            return self.current_amount >= self.target_amount
        except Exception as e:
            logger.error(f"Error checking completion for goal {self.id}: {e}")
            return False
    
    def add_savings(self, amount):
        """Add savings to the goal."""
        try:
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
            
            self.current_amount += Decimal(str(amount))
            self.save()
            
            logger.info(f"Added ₱{amount} to goal {self.id}. New total: ₱{self.current_amount}")
            return True
        except Exception as e:
            logger.error(f"Error adding savings to goal {self.id}: {e}")
            raise
    
    def mark_complete(self):
        """Mark goal as completed."""
        try:
            from django.utils import timezone
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            
            logger.info(f"Goal {self.id} marked as completed")
            return True
        except Exception as e:
            logger.error(f"Error marking goal {self.id} as complete: {e}")
            raise
    
    def reset_progress(self):
        """Reset progress to zero."""
        try:
            self.current_amount = Decimal('0.00')
            self.status = 'active'
            self.completed_at = None
            self.save()
            
            logger.info(f"Goal {self.id} progress reset to zero")
            return True
        except Exception as e:
            logger.error(f"Error resetting goal {self.id}: {e}")
            raise
    
    def archive(self):
        """Archive the goal."""
        try:
            self.status = 'archived'
            self.save()
            
            logger.info(f"Goal {self.id} archived")
            return True
        except Exception as e:
            logger.error(f"Error archiving goal {self.id}: {e}")
            raise


class SavingsTransaction(models.Model):
    """Model for tracking individual savings contributions to goals."""
    
    TRANSACTION_TYPE_CHOICES = [
        ('add', 'Add Savings'),
        ('withdraw', 'Withdraw'),
        ('reset', 'Reset'),
    ]
    
    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='add'
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['goal', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type.title()} ₱{self.amount} - {self.goal.name}"
