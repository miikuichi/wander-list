from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import BudgetAlertForm
from .models import BudgetAlert, Category

def alerts_page(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        categories = Category.objects.filter(user=request.user).order_by("name")
        
        if not categories.exists():
            for n in ["Food", "Transport", "Leisure", "Bills", "School Supplies"]:
                Category.objects.get_or_create(user=request.user, name=n)
            categories = Category.objects.filter(user=request.user).order_by("name")
    else:
        categories = []

    # Handle form submission for creating a new budget alert
    if request.method == "POST":
        form = BudgetAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            #if request.user.is_authenticated:
            alert.user = request.user
            alert.save()
            messages.success(request, "Budget alert saved successfully.")
            return redirect("alerts_page")
    else:
        form = BudgetAlertForm()

    # Fetch only active budget alerts for the logged-in user
    alerts = BudgetAlert.objects.filter(user=request.user, active=True) if request.user.is_authenticated else []

    # Pass categories, form, and alerts to the template
    return render(request, "budget_alerts/alerts.html", {
        "form": form,
        "alerts": alerts,
        "categories": categories 
    })

def edit_alert(request, id):
    alert = get_object_or_404(BudgetAlert, id=id)

    if request.method == "POST":
        form = BudgetAlertForm(request.POST, instance=alert)
        
        if form.is_valid():
            alert = form.save(commit=False)
            alert.active = True
            alert.save()

            messages.success(request, "Budget alert updated successfully.")
            return redirect("alerts_page")

    else:
        form = BudgetAlertForm(instance=alert)

    # Pass the form, alert, and categories to the template for rendering
    return render(request, "budget_alerts/alerts.html", {
        "form": form,
        "alert": alert,
        "categories": Category.objects.filter(user=request.user)
    })

def delete_alert(request, id):
    alert = get_object_or_404(BudgetAlert, id=id)
    alert.delete()
    print(BudgetAlert.objects.count())
    messages.success(request, "Budget alert deleted successfully.")
    return redirect('alerts_page')

