# login/urls.py

from django.urls import path
from . import views

app_name = 'login'

urlpatterns = [
    # This maps the URL path 'login/' to the 'login_view' function
    path('', views.login_view, name='login_page'),
    path('register/', views.register, name='register_page'),
    #logout functionality
    path('logout/', views.logout_view, name='logout'), 
]