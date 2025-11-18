# expenses/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.expenses_view, name='expenses'),
    path('add-income/', views.add_income_view, name='add_income'),
    path('edit/<int:expense_id>/', views.edit_expense_view, name='edit_expense'),
    path('delete/<int:expense_id>/', views.delete_expense_view, name='delete_expense'),
]

