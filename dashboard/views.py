from django.shortcuts import render
from django.shortcuts import redirect

def dashboard_view(request):
    """Display dashboard for authenticated users.
    
    Authentication is handled by the SupabaseAuthMiddleware.
    """
    # This will only execute if the user is authenticated (middleware allows the request)
    username = request.session.get('username', 'User')
    email = request.session.get('email', '')
    
    context = {
        'username': username,
        'email': email,
        'user_id': request.session.get('user_id'),
    }
    return render(request, 'dashboard/dashboard.html', context)
