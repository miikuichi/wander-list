from django.shortcuts import render



def expenses_view(request):
    return render(request, 'expenses/expenses.html')