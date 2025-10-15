# dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.expenses_view, name='expenses'),
    path('delete/<int:id>/', views.delete_expense, name='delete_expense'),
]

