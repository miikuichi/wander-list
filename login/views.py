from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from .forms import LoginForm, RegistrationForm
from supabase_service import sign_up, sign_in, get_service_client, get_anon_client
from .models import User
from audit_logs.services import log_login, log_create, log_logout
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
                        }
                    )
                    if created:
                        user.set_password(password)  # Hash the password
                        user.save()
                    return render(request, 'login/register.html', {'form': form})

                # Store user in local SQLite with hashed password
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                    }
                )

                if created:
                    user.set_password(password)  # Hash the password on creation
                    user.save()
                    # Log user creation
                    log_create(str(user.id), 'user', user.id, {'username': username, 'email': email}, request)
                else:
                    # User already exists, update username and hash password
                    user.username = username
                    user.set_password(password)  # Hash the updated password
                    user.save()

                # ALSO insert into Supabase PostgreSQL using REST API
                # Note: Supabase handles its own password hashing in Auth
                remote_user_id = None
                try:
                    supabase_client = get_service_client()
                    
                    print(f"DEBUG: Attempting to insert user into Supabase login_user table...")
                    print(f"DEBUG: Email: {email}, Username: {username}")
                    
                    # Insert new user WITHOUT specifying ID (let Supabase auto-generate)
                    # Note: We store a hashed version of the password in the table
                    # even though Supabase Auth manages authentication
                    # This is required because the login_user table has a NOT NULL constraint
                    from django.contrib.auth.hashers import make_password
                    hashed_password = make_password(password)
                    
                    insert_response = supabase_client.table('login_user').insert({
                        'username': username,
                        'email': email,
                        'password': hashed_password,  # Store hashed password to satisfy NOT NULL constraint
                        'is_admin': False,
                    }).execute()
                    
                    print(f"DEBUG: Insert response received")
                    print(f"DEBUG: Response data: {insert_response.data}")
                    
                    # Get the actual ID assigned by Supabase
                    if insert_response.data and len(insert_response.data) > 0:
                        remote_user_id = insert_response.data[0]['id']
                        logger.info(f"User {email} saved to Supabase PostgreSQL with ID: {remote_user_id}")
                        print(f"DEBUG: ✅ Successfully inserted user with ID: {remote_user_id}")
                    else:
                        logger.error(f"Failed to get remote user ID after insert")
                        print(f"DEBUG: ❌ Insert response had no data!")
                        remote_user_id = user.id  # Fallback to local ID
                        
                except Exception as db_error:
                    error_str = str(db_error)
                    print(f"DEBUG: ❌ Exception during Supabase insert: {error_str}")
                    print(f"DEBUG: Exception type: {type(db_error)}")
                    import traceback
                    traceback.print_exc()
                    
                    # Handle duplicate user (user already exists in Supabase)
                    if '23505' in error_str or 'duplicate key value violates unique constraint' in error_str:
                        logger.info(f"User {email} already exists in Supabase, fetching existing ID...")
                        print(f"DEBUG: User already exists, fetching ID...")
                        try:
                            existing_user = supabase_client.table('login_user').select('id').eq('email', email).single().execute()
                            if existing_user.data:
                                remote_user_id = existing_user.data['id']
                                logger.info(f"Fetched existing user ID: {remote_user_id}")
                                print(f"DEBUG: ✅ Fetched existing user ID: {remote_user_id}")
                        except Exception as fetch_error:
                            logger.error(f"Failed to fetch existing user ID: {fetch_error}")
                            print(f"DEBUG: ❌ Failed to fetch existing ID: {fetch_error}")
                            remote_user_id = user.id  # Fallback
                    else:
                        logger.error(f"Failed to save to Supabase PostgreSQL: {db_error}")
                        print(f"DEBUG: ❌ Unexpected error, using fallback local ID")
                        remote_user_id = user.id  # Fallback to local ID

                # Store authentication info in session using REMOTE user_id
                if not remote_user_id:
                    print(f"DEBUG: ⚠️  remote_user_id is None, using local ID as final fallback")
                    remote_user_id = user.id  # Final fallback
                
                print(f"DEBUG: Setting session user_id to: {remote_user_id}")
                    
                request.session['user_id'] = remote_user_id
                request.session['username'] = username
                request.session['email'] = email
                request.session['is_admin'] = False

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

                # Get Supabase Client
                supabase = get_service_client()

                # Debugging: Print the raw response type to understand what we got back
                print(f"DEBUG: Supabase response type: {type(signin_response)}")

                db_user_response = supabase.table('login_user')\
                    .select('*')\
                    .eq('email', email)\
                    .single()\
                    .execute()
                if not db_user_response.data:
                    raise ValueError("User logged in but not found in Supabase 'login_user' table.")

                # Extract access_token and user_data safely
                access_token = None
                user_data = None

                remote_user = db_user_response.data
                remote_user_id = remote_user['id']  # This is the correct ID (e.g., 6 for gwapo)
                is_admin = remote_user.get('is_admin', False)

                # Sync Local SQLite User (Just for Admin Dashboard display)
                user, created = User.objects.update_or_create(
                    email=email,
                    defaults={
                        'username': remote_user.get('username', email.split('@')[0]),
                        'is_admin': is_admin,
                        # We don't rely on the local ID anymore, so we just ensure the record exists
                    }
                )

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
                request.session['user_id'] = remote_user_id
                request.session['username'] = user.username
                request.session['email'] = email
                request.session['is_admin'] = is_admin

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
    """Handle OAuth callback from Google/Supabase with correct ID syncing."""
    try:
        # Extract access_token
        access_token = request.GET.get('access_token') or request.POST.get('access_token')

        if not access_token:
            messages.error(request, "⚠️ OAuth authentication failed. No access token received.")
            return redirect('login:login_page')

        # 1. Get Supabase Client
        supabase = get_service_client()

        # 2. Verify Token & Get User Email
        response = supabase.auth.get_user(access_token)

        if not response or not hasattr(response, 'user'):
            messages.error(request, "⚠️ Failed to retrieve user information from Google.")
            return redirect('login:login_page')

        user_data = response.user
        email = user_data.email

        # Extract metadata
        user_metadata = user_data.user_metadata or {}
        username = user_metadata.get('name', email.split('@')[0])

        # ---------------------------------------------------------
        # CRITICAL FIX: Fetch REAL ID from Supabase 'login_user'
        # ---------------------------------------------------------
        remote_user_id = None
        is_admin = False

        try:
            # Try to find the user in Supabase public table
            db_user_response = supabase.table('login_user')\
                .select('*')\
                .eq('email', email)\
                .single()\
                .execute()

            if db_user_response.data:
                # User exists! Grab their REAL ID
                remote_user = db_user_response.data
                remote_user_id = remote_user['id']
                is_admin = remote_user.get('is_admin', False)
                logger.info(f"Found existing OAuth user in Supabase: {email} (ID: {remote_user_id})")

        except Exception as e:
            logger.warning(f"User {email} not found in login_user table yet: {e}")

        # ---------------------------------------------------------
        # Sync Local User (Update or Create)
        # ---------------------------------------------------------
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                'username': username,
                'password': 'oauth_google',
                'is_admin': is_admin
            }
        )

        # ---------------------------------------------------------
        # Handle New Users (If not in Supabase yet)
        # ---------------------------------------------------------
        if not remote_user_id:
            # This is a NEW user (or sync issue). We must insert them into Supabase.
            # We try to let Supabase handle the ID, or use local if necessary.
            try:
                # Insert and return the created record to get the ID
                new_user_data = {
                    'username': username,
                    'email': email,
                    'password': 'oauth_google',
                    'is_admin': False
                }
                # Insert and select back the ID
                insert_response = supabase.table('login_user').insert(new_user_data).select().execute()

                if insert_response.data:
                    remote_user_id = insert_response.data[0]['id']
                    logger.info(f"Created new OAuth user in Supabase: {email} (ID: {remote_user_id})")
                else:
                    # Fallback (rare): Use local ID if insert didn't return data
                    remote_user_id = user.id

            except Exception as insert_error:
                error_str = str(insert_error)

                # Check for the specific database conflict error (PostgreSQL code 23505)
                # or a Supabase error message indicating duplicate key.
                if '23505' in error_str or 'duplicate key value violates unique constraint' in error_str:
                    logger.warning(f"OAuth user {email} already exists. Skipping insert due to conflict.")
                    # Treat conflict as success and continue the login flow
                    # We must re-run the GET to fetch the correct remote_user_id now!
                    try:
                        db_user_response = supabase.table('login_user')\
                            .select('*')\
                            .eq('email', email)\
                            .single()\
                            .execute()
                        if db_user_response.data:
                             remote_user_id = db_user_response.data[0]['id']
                        else:
                             # Worst-case fallback
                             remote_user_id = user.id
                    except:
                        remote_user_id = user.id

                else:
                    # If it's a different, unexpected error, raise it
                    logger.error(f"Failed to create OAuth user in Supabase (Unexpected): {insert_error}")
                    remote_user_id = user.id # Emergency fallback

        # ---------------------------------------------------------
        # SESSION SETUP (Use Remote ID)
        # ---------------------------------------------------------
        request.session['user_id'] = remote_user_id  # <--- THE FIX
        request.session['username'] = username
        request.session['email'] = email
        request.session['is_admin'] = is_admin
        request.session['supabase_access_token'] = access_token
        request.session['auth_method'] = 'google_oauth'

        # Redirect Logic
        if is_admin:
            messages.success(request, f"✅ Welcome Admin, {username}!")
            return redirect('admin_dashboard')
        else:
            messages.success(request, f"✅ Welcome, {username}!")
            return redirect('dashboard')

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        messages.error(request, f"⚠️ Authentication failed: {str(e)}")
        return redirect('login:login_page')


def logout_and_redirect(request):
    """Log out user from both Django session and Supabase"""
    # Log the logout before clearing session
    user_id = request.session.get('user_id')
    if user_id:
        log_logout(str(user_id), request=request)

    # Clear all session data
    request.session.flush()
    return redirect('login:login_page')


def bridge(request):
    # Renders the page that reads #access_token and posts it to /login/callback/
    return render(request, 'login/bridge.html')
