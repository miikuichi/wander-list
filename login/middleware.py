from django.shortcuts import redirect
from django.urls import reverse

class SupabaseAuthMiddleware:
    """Middleware to check if user is authenticated via Supabase."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Paths that don't require authentication
        exempt_paths = [
            '/login/',
            '/login/register/',
            '/admin/',
        ]
        
        # Check if the path is exempt
        path_is_exempt = any(request.path.startswith(path) for path in exempt_paths)
        
        # If path needs authentication and user is not authenticated, redirect to login
        if not path_is_exempt and 'user_id' not in request.session:
            return redirect('login:login_page')
            
        # Add user info to request for templates
        if 'user_id' in request.session:
            request.user_authenticated = True
            request.username = request.session.get('username')
        else:
            request.user_authenticated = False
            
        response = self.get_response(request)
        return response