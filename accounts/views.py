from django.shortcuts import render
from supabase import create_client, Client

SUPABASE_URL = "https://miwckqsyomyxloyppsuj.supabase.co"
SUPABASE_KEY = "sb_secret_DJgFyS62I1_yd2FEK-l4RA_uaCzW-Xu"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_view(request):
    banner = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = supabase.table("users").select("id").eq("username", username).eq("password", password).execute()
        if user.data:
            banner = "Login successful!"
        else:
            banner = "Incorrect username or password."
    return render(request, 'accounts/login.html', {"banner": banner})

def register_view(request):
    banner = ""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        # Check if username already exists
        existing = supabase.table("users").select("id").eq("username", username).execute()
        if existing.data:
            banner = "Username already exists."
        else:
            result = supabase.table("users").insert({
                "username": username,
                "password": password,
                "email": email
            }).execute()
            print("Registration result:", result)  # Log to console
            if result.data:
                banner = "<script>alert('Registration successful!');</script>Registration successful!"
            else:
                banner = "Registration failed."
    return render(request, 'accounts/register.html', {"banner": banner})
