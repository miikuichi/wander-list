# dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.expenses_view, name='expenses'),
]