from django.urls import path
from . import views

app_name = 'savings_goals'

urlpatterns = [
    path('', views.savings_goals_view, name='goals'),
    path('edit/<int:goal_id>/', views.edit_goal_view, name='edit_goal'),
    path('delete/<int:goal_id>/', views.delete_goal_view, name='delete_goal'),
    path('add-savings/<int:goal_id>/', views.add_savings_view, name='add_savings'),
    path('achieve/<int:goal_id>/', views.achieve_goal_view, name='achieve_goal'),
    path('reset/<int:goal_id>/', views.reset_goal_view, name='reset_goal'),
]
