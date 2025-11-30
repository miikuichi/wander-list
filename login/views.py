from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from .forms import LoginForm, RegistrationForm
from supabase_service import sign_up, sign_in, get_service_client, get_anon_client
from .models import User
import traceback

logger = logging.getLogger(__name__)

def register(request):
    """Handles user registration using Supabase authentication."""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in request.session:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                # First create the user in Supabase auth
                signup_response = sign_up(email, password)
                
                # Log the response for debugging
                logger.info(f"Supabase signup response: {signup_response}")
                print(f"DEBUG: Supabase signup response type: {type(signup_response)}")
                print(f"DEBUG: Supabase signup response: {signup_response}")
                
                # Extract access_token and user from response
                access_token = None
                user_data = None
                
                # Handle AuthResponse object (from supabase_auth package)
                if hasattr(signup_response, 'user'):
                    user_data = signup_response.user
                if hasattr(signup_response, 'session'):
                    # Session might be None if email confirmation is required
                    if signup_response.session and hasattr(signup_response.session, 'access_token'):
                        access_token = signup_response.session.access_token
                
                # Fallback for dict response (older client versions)
                if isinstance(signup_response, dict):
                    session_data = signup_response.get('session', {})
                    user_data = user_data or signup_response.get('user', {})
                    if isinstance(session_data, dict):
                        access_token = access_token or session_data.get('access_token')
                
                # Check if user was actually created
                if not user_data:
                    raise ValueError("User registration failed: No user data returned from Supabase")
                
                # If session is None, email confirmation is likely required
                if not access_token and hasattr(signup_response, 'session') and signup_response.session is None:
                    messages.warning(request, "⚠️ Please check your email to confirm your account before logging in.")
                    # Still create the local user but don't log them in
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': username,
                            'password': "hashed_via_supabase"
                        }
                    )
                    return render(request, 'login/register.html', {'form': form})
                
                # Store user in local SQLite
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'password': password  # Storing unhashed for testing
                    }
                )
                
                if not created:
                    # User already exists, update username and password
                    user.username = username
                    user.password = password  # Update unhashed password for testing
                    user.save()
                
                # ALSO insert into Supabase PostgreSQL using REST API
                try:
                    supabase_client = get_service_client()
                    supabase_client.table('login_user').upsert({
                        'id': user.id,
                        'username': username,
                        'email': email,
                        'password': password  # Unhashed for testing
                    }).execute()
                    logger.info(f"User {email} saved to Supabase PostgreSQL")
                except Exception as db_error:
                    logger.error(f"Failed to save to Supabase PostgreSQL: {db_error}")
                    # Continue anyway - user is in SQLite and Supabase Auth
                
                # Store authentication info in session
                request.session['user_id'] = user.id
                request.session['username'] = username
                request.session['email'] = email
                
                if access_token:
                    request.session['supabase_access_token'] = access_token
                
                messages.success(request, "🎉 Registration successful. Welcome aboard!")
                return redirect('dashboard')
            except Exception as e:
                logger.error(f"Registration failed: {e}")
                print(f"DEBUG: Registration error: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"⚠️ Registration failed: {str(e)}")
                # Don't redirect on error - stay on registration page
        else:
            # Log detailed errors to console
            logger.error("Form validation failed: %s", form.errors.as_json())
            messages.error(request, "⚠️ Registration failed. Please check the form for errors.")
    else:
        form = RegistrationForm()
    return render(request, 'login/register.html', {'form': form})


def login_view(request):
    """Handles user login with enhanced debugging and error tracing."""
    
    # 0. Session Check: If already logged in, redirect immediately
    if 'user_id' in request.session:
        print(f"DEBUG: User {request.session.get('username')} already in session. Redirecting.")
        if request.session.get('is_admin'):
            return redirect('admin_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            print(f"DEBUG: Starting login process for email: {email}")

            try:
                # ---------------------------------------------------------
                # STEP 1: Supabase Authentication
                # ---------------------------------------------------------
                print("DEBUG: Step 1 - Calling Supabase sign_in...")
                signin_response = sign_in(email, password)
                
                # Debugging: Print the raw response type to understand what we got back
                print(f"DEBUG: Supabase response type: {type(signin_response)}")
                
                # Extract access_token and user_data safely
                access_token = None
                user_data = None
                
                # Handle different Supabase client response structures
                if hasattr(signin_response, 'user'):
                    user_data = signin_response.user
                
                if hasattr(signin_response, 'session'):
                    # Check if session exists and has access_token
                    if signin_response.session and hasattr(signin_response.session, 'access_token'):
                        access_token = signin_response.session.access_token
                
                # Fallback for dictionary responses (older clients)
                if isinstance(signin_response, dict):
                    session_data = signin_response.get('session', {})
                    user_data = user_data or signin_response.get('user', {})
                    if isinstance(session_data, dict):
                        access_token = access_token or session_data.get('access_token')
                
                if not user_data:
                    # If we reached here, Supabase didn't return a user. Throw error to catch block.
                    raise ValueError(f"Login failed: No user data returned. Raw response: {signin_response}")
                
                print("DEBUG: Step 1 Success - Supabase User authenticated.")

                # ---------------------------------------------------------
                # STEP 2: Local Database Sync (Get or Create)
                # ---------------------------------------------------------
                print("DEBUG: Step 2 - Syncing with local SQLite database...")
                try:
                    user = User.objects.get(email=email)
                    print(f"DEBUG: Local user found: {user.username} (ID: {user.id})")
                    welcome_message = f"Welcome back, {user.username}!"
                except User.DoesNotExist:
                    print("DEBUG: User not found locally. Creating new local user...")
                    username = email.split('@')[0]
                    user = User.objects.create(
                        username=username,
                        email=email,
                        password=password  # Note: In production, hash this!
                    )
                    print(f"DEBUG: New local user created: {user.username} (ID: {user.id})")
                    welcome_message = f"Welcome, {username}!"

                # ---------------------------------------------------------
                # STEP 3: Admin Status Sync (Supabase DB -> Local DB)
                # ---------------------------------------------------------
                print("DEBUG: Step 3 - Checking Admin Status from Supabase...")
                try:
                    supabase = get_service_client()
                    # Query the 'login_user' table in Supabase
                    response = supabase.table('login_user').select('is_admin').eq('email', email).execute()
                    
                    if response.data and len(response.data) > 0:
                        remote_is_admin = response.data[0].get('is_admin', False)
                        print(f"DEBUG: Supabase reports is_admin = {remote_is_admin}")
                        
                        # Only write to DB if the status has changed
                        if user.is_admin != remote_is_admin:
                            user.is_admin = remote_is_admin
                            user.save()
                            print(f"DEBUG: Local DB updated. User {user.username} is_admin set to {remote_is_admin}")
                    else:
                        print("DEBUG: User not found in 'login_user' table on Supabase (Admin check skipped).")
                            
                except Exception as sync_error:
                    # We catch this separately so login doesn't fail just because admin-sync failed
                    print("DEBUG: [WARNING] Admin sync failed.")
                    print("vvvvvvvvv ADMIN SYNC ERROR vvvvvvvvv")
                    traceback.print_exc()
                    print("^^^^^^^^^ ADMIN SYNC ERROR ^^^^^^^^^")
                    logger.error(f"Failed to sync admin status: {sync_error}")

                # ---------------------------------------------------------
                # STEP 4: Session Setup
                # ---------------------------------------------------------
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['email'] = email
                request.session['is_admin'] = user.is_admin
                
                if access_token:
                    request.session['supabase_access_token'] = access_token
                
                print(f"DEBUG: Step 4 Success - Session set. Admin: {user.is_admin}")
                messages.success(request, welcome_message)

                # ---------------------------------------------------------
                # STEP 5: Redirect
                # ---------------------------------------------------------
                if user.is_admin:
                    print("DEBUG: Redirecting to ADMIN dashboard.")
                    return redirect('admin_dashboard')
                else:
                    print("DEBUG: Redirecting to USER dashboard.")
                    return redirect('dashboard')

            except Exception as e:
                # ---------------------------------------------------------
                # CRITICAL ERROR HANDLING
                # ---------------------------------------------------------
                print("\n" + "="*50)
                print("CRITICAL LOGIN ERROR ENCOUNTERED")
                print("="*50)
                print(f"Error Message: {str(e)}")
                print("-" * 20 + " TRACEBACK START " + "-" * 20)
                
                # This prints the full stack trace to your terminal
                traceback.print_exc()
                
                print("-" * 20 + " TRACEBACK END " + "-" * 20)
                print("="*50 + "\n")
                
                # Also log to Django's standard logging (good for production logs)
                logger.error(f"Login View Exception: {e}", exc_info=True)
                
                messages.error(request, f"Login failed: {str(e)}")
                # Stay on login page
        else:
            print(f"DEBUG: Form validation failed. Errors: {form.errors}")
            messages.error(request, "Login failed. Please check your email and password.")
    else:
        form = LoginForm()
        
    return render(request, 'login/login.html', {'form': form})
def google_login(request):
    """Initiate Google OAuth login flow."""
    try:
        supabase = get_anon_client()
        
        # Get the redirect URL (where Google will send user back)
        redirect_url = request.build_absolute_uri('/login/bridge/')

        
        # This generates the OAuth URL but doesn't redirect
        # We'll use JavaScript to handle the actual redirect
        oauth_url = f"https://{supabase.supabase_url.replace('https://', '')}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"
        
        return JsonResponse({
            'success': True,
            'oauth_url': oauth_url
        })
        
    except Exception as e:
        logger.error(f"Google OAuth initiation failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def oauth_callback(request):
    """Handle OAuth callback from Google/Supabase."""
    try:
        # Extract access_token from URL fragment or query params
        # Supabase sends tokens in URL fragment (after #)
        # These need to be parsed by JavaScript and sent to this endpoint
        
        access_token = request.GET.get('access_token') or request.POST.get('access_token')
        refresh_token = request.GET.get('refresh_token') or request.POST.get('refresh_token')
        
        if not access_token:
            messages.error(request, "⚠️ OAuth authentication failed. No access token received.")
            return redirect('login:login_page')
        
        # Get user info from Supabase using the access token
        supabase = get_service_client()
        
        # Use the access token to get user details
        response = supabase.auth.get_user(access_token)
        
        if not response or not hasattr(response, 'user'):
            messages.error(request, "⚠️ Failed to retrieve user information from Google.")
            return redirect('login:login_page')
        
        user_data = response.user
        email = user_data.email
        
        # Extract name from user metadata
        user_metadata = user_data.user_metadata or {}
        full_name = user_metadata.get('full_name', '')
        username = user_metadata.get('name', email.split('@')[0])
        
        # Store user in local SQLite
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'password': 'oauth_google'  # Placeholder for OAuth users
            }
        )
        
        if not created and user.password != 'oauth_google':
            # Update existing user to indicate OAuth login
            user.username = username
            user.save()
        
        # Store in Supabase PostgreSQL
        try:
            supabase.table('login_user').upsert({
                'id': user.id,
                'username': username,
                'email': email,
                'password': 'oauth_google'
            }).execute()
            logger.info(f"OAuth user {email} saved to Supabase")
        except Exception as db_error:
            logger.error(f"Failed to save OAuth user to Supabase: {db_error}")
        
        # Create session
        request.session['user_id'] = user.id
        request.session['username'] = username
        request.session['email'] = email
        request.session['supabase_access_token'] = access_token
        request.session['auth_method'] = 'google_oauth'
        
        messages.success(request, f"✅ Welcome, {username}! Signed in with Google.")
        return redirect('dashboard')
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        messages.error(request, f"⚠️ Authentication failed: {str(e)}")
        return redirect('login:login_page')

def logout_and_redirect(request):
    """Log out user from both Django session and Supabase"""
    # Clear all session data
    request.session.flush()
    return redirect('login:login_page')


def bridge(request):
    # Renders the page that reads #access_token and posts it to /login/callback/
    return render(request, 'login/bridge.html')