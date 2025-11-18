from django.shortcuts import redirect
from django.urls import reverse

class SupabaseAuthMiddleware:
    """Middleware to check if user is authenticated via Supabase."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check if user is authenticated
        is_authenticated = 'user_id' in request.session
        
        # Paths that don't require authentication
        public_paths = [
            '/login/',
            '/login/register/',
            '/login/bridge/',
            '/login/callback/',
            '/login/google/',
            '/admin/',
        ]
        
        # Check if the path is public
        path_is_public = any(request.path.startswith(path) for path in public_paths)
        
        # If user is authenticated and trying to access login/register, redirect to dashboard
        if is_authenticated and request.path in ['/login/', '/login/register/']:
            return redirect('dashboard')
        
        # If path needs authentication and user is not authenticated, redirect to login
        if not path_is_public and not is_authenticated:
            return redirect('login:login_page')
            
        # Add user info to request for templates
        if 'user_id' in request.session:
            request.user_authenticated = True
            request.username = request.session.get('username')
        else:
            request.user_authenticated = False
            
        response = self.get_response(request)
        return response