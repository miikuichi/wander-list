from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, logout # <-- Combined imports

# FIX 1: Import all necessary components from supabase client
try:
    from supabase import create_client, Client
    # Define the client variable, but DON'T execute the setup code yet
    SUPABASE_CLIENT_STATUS = True
except ImportError:
    # Handle the case where the package isn't installed by setting a flag
    # This prevents the server from crashing if you choose not to install it.
    SUPABASE_CLIENT_STATUS = False
    print("WARNING: Supabase client library not found. Supabase-related functions will fail.")


# FIX 2: Create the Supabase client inside an 'if' block or a function
# This ensures it is only run after the necessary settings have been loaded.
if SUPABASE_CLIENT_STATUS:
    try:
        # Check if settings are available before creating the client
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except AttributeError:
        # Handle case where SUPABASE_URL/KEY is missing in settings.py
        print("ERROR: SUPABASE_URL or SUPABASE_KEY is missing in Django settings.")
        SUPABASE_CLIENT_STATUS = False
else:
    # Define 'supabase' as None if the client package is missing
    supabase = None
    


def register(request):
    """Handles user registration using Django's built-in form."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login:login_page')
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = UserCreationForm()
    return render(request, 'login/register.html', {'form': form})

def login_view(request):
    """Handles user login using Django's built-in authentication."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()

    context = {
        'form': form
    }
    return render(request, 'login/login.html', context)

def supabase_login_view(request):
    """Handles user login by querying the Supabase database directly."""
    banner = ""
    # FIX 3: Add a check to ensure the client is available
    if not SUPABASE_CLIENT_STATUS:
        banner = "Supabase service is unavailable due to missing client package or configuration."
        return render(request, 'login/login.html', {"banner": banner})

    if request.method == "POST":
        # Note: You should generally use email/password for Supabase Auth,
        # and this plain query is highly insecure for production!
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        # The Supabase query logic
        user = supabase.table("users").select("id").eq("username", username).eq("password", password).execute()
        
        if user.data:
            banner = "Login successful!"
            # You should set a session here if the user is authenticated
            # return redirect('dashboard')
        else:
            banner = "Incorrect username or password."
    return render(request, 'login/login.html', {"banner": banner})

def logout_view(request):
    """Logs out the user and redirects to the login page."""
    logout(request)
    return redirect('login:login_page')