from django.core.management.base import BaseCommand
from django.conf import settings

from supabase_service import get_service_client, sign_up, sign_in


class Command(BaseCommand):
    help = "Test Supabase connection and optionally populate a sample row."

    def add_arguments(self, parser):
        parser.add_argument('--create-user', action='store_true', help='Create a test user via Supabase auth (anon client)')
        parser.add_argument('--email', type=str, default='test@example.com', help='Test user email')
        parser.add_argument('--password', type=str, default='password123', help='Test user password')
        parser.add_argument('--table', type=str, default='budget_alerts_alert', help='Table to insert into (Supabase public schema)')
        parser.add_argument('--use-user-client', action='store_true', help='After signing in, attempt the insert using the user-scoped client (base auth)')

    def handle(self, *args, **options):
        # Try to create a service client and insert a sample row
        try:
            client = get_service_client()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to create service client: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('Created service client'))

        # Optionally create a user via auth
        if options['create_user']:
            email = options['email']
            password = options['password']
            try:
                resp = sign_up(email, password)
                self.stdout.write(self.style.SUCCESS(f'Sign-up response: {resp}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to sign up user: {e}'))

        user_client = None
        if options.get('use_user_client') and options['create_user']:
            # Try to sign in and get a user-scoped client
            try:
                signin = sign_in(options['email'], options['password'])
                # signin typically returns a dict with session/access_token
                access_token = None
                if isinstance(signin, dict):
                    # new client versions have {'session': {'access_token': '...'}}
                    session = signin.get('session') or signin.get('data', {}).get('session')
                    if session and isinstance(session, dict):
                        access_token = session.get('access_token') or session.get('accessToken')
                    # older returns may have {'access_token': '...'} at top level
                    access_token = access_token or signin.get('access_token') or signin.get('accessToken')
                # Fallback: if the object has a 'get' method but isn't a dict
                if not access_token and hasattr(signin, 'get'):
                    try:
                        access_token = signin.get('access_token')
                    except Exception:
                        pass

                if access_token:
                    from supabase_service import get_user_client
                    user_client = get_user_client(access_token)
                    self.stdout.write(self.style.SUCCESS('Obtained user-scoped client'))
                else:
                    self.stderr.write(self.style.WARNING('Could not locate access token in sign-in response; user client unavailable'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to sign in user: {e}'))

        # Insert a sample row into the provided table. The table name should exist in your
        # Supabase Postgres DB. This example inserts a minimal row; change columns as needed.
        table = options['table']
        try:
            data = {"note": "populated-by-management-command"}
            target_client = user_client if user_client is not None else client
            insert_resp = target_client.table(table).insert(data).execute()
            self.stdout.write(self.style.SUCCESS(f'Insert response: {insert_resp}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to insert into table {table}: {e}'))