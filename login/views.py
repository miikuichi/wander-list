from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect
from supabase import create_client, Client

from django.conf import settings
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout # <--- IMPORT THIS



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login:login_page') # Redirect to the login page
        else:
            # THIS IS THE CRUCIAL LINE FOR DEBUGGING:
            print("FORM ERRORS:", form.errors)
    else:
        form = UserCreationForm()
    return render(request, 'login/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect to a success page after login
            return redirect('dashboard')
    else:
        form = AuthenticationForm()

    context = {
        'form': form
    }
    return render(request, 'login/login.html', context)

# Alternative: Supabase login
def supabase_login_view(request):
    banner = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = supabase.table("users").select("id").eq("username", username).eq("password", password).execute()
        if user.data:
            banner = "Login successful!"
            # You can redirect to dashboard or another page here
            # return redirect('dashboard')
        else:
            banner = "Incorrect username or password."
    return render(request, 'login/login.html', {"banner": banner})

def logout_view(request):
    """Logs out the user and redirects to the login page."""
    
    # Clears the user's session and removes their authentication cookie
    logout(request) 
    
    # Redirect to the login page after logging out
    return redirect('login:login_page') 