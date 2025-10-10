from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ExpenseForm
from .models import Expense, Category # 💡 FIX: Added missing imports

# Assuming expense_list and expenses_view are also in this file:

@login_required
def expenses_view(request):
    """
    Displays the expenses page and handles new expense submissions.
    GET: Renders the page with the form and recent expenses.
    POST: Validates and saves the Expense then redirects (PRG) back to this view.
    """
    # Build categories for the form and sidebar
    categories = Category.objects.filter(user=request.user).order_by('name')

    # If the user has no categories yet, create some sensible defaults (same behavior as budget_alerts.alerts_page)
    if not categories.exists():
        default_names = ["Food", "Transport", "Leisure", "Bills", "School Supplies"]
        for n in default_names:
            Category.objects.get_or_create(user=request.user, name=n)
        categories = Category.objects.filter(user=request.user).order_by('name')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            new_expense = form.save(commit=False)
            new_expense.user = request.user
            new_expense.save()
            # Redirect after successful POST to avoid double submissions
            return redirect('expenses')
    else:
        form = ExpenseForm(user=request.user)

    # Recent expenses shown on the page
    recent_expenses = Expense.objects.filter(user=request.user).order_by('-date', '-created_at')[:10]

    context = {
        'form': form,
        'categories': categories,
        'recent_expenses': recent_expenses,
    }
    return render(request, 'expenses/expenses.html', context)
