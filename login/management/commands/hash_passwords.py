"""
Management command to hash existing plaintext passwords in the database.
Run this once to migrate from plaintext to hashed passwords.

Usage: python manage.py hash_passwords
"""
from django.core.management.base import BaseCommand
from login.models import User
from django.db import transaction


class Command(BaseCommand):
    help = 'Hashes all plaintext passwords in the User database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('PASSWORD HASHING MIGRATION'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN MODE - No changes will be made\n'))
        
        # Get all users
        users = User.objects.all()
        total_users = users.count()
        
        if total_users == 0:
            self.stdout.write(self.style.WARNING('No users found in database.'))
            return
        
        self.stdout.write(f'Found {total_users} users in database.\n')
        
        hashed_count = 0
        already_hashed_count = 0
        oauth_count = 0
        error_count = 0
        
        with transaction.atomic():
            for user in users:
                # Check if password is already hashed
                if user.password.startswith('pbkdf2_'):
                    already_hashed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ {user.email} - Already hashed')
                    )
                    continue
                
                # Check if OAuth user
                if user.password in ['oauth_google', 'oauth_google_no_password', 'hashed_via_supabase']:
                    oauth_count += 1
                    self.stdout.write(
                        self.style.NOTICE(f'⊙ {user.email} - OAuth user, setting secure placeholder')
                    )
                    if not dry_run:
                        user.set_password('oauth_google_no_password')
                        user.save()
                    continue
                
                # Hash plaintext password
                try:
                    plaintext = user.password
                    
                    if not dry_run:
                        user.set_password(plaintext)
                        user.save()
                    
                    hashed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ {user.email} - Password hashed')
                    )
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'✗ {user.email} - Error: {str(e)}')
                    )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('\nMIGRATION SUMMARY:'))
        self.stdout.write('='*60)
        self.stdout.write(f'Total users:          {total_users}')
        self.stdout.write(self.style.SUCCESS(f'Newly hashed:         {hashed_count}'))
        self.stdout.write(self.style.NOTICE(f'Already hashed:       {already_hashed_count}'))
        self.stdout.write(self.style.NOTICE(f'OAuth users:          {oauth_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors:               {error_count}'))
        self.stdout.write('='*60 + '\n')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN COMPLETE - Run without --dry-run to apply changes')
            )
        elif hashed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully hashed {hashed_count} passwords!')
            )
        else:
            self.stdout.write(
                self.style.NOTICE('All passwords are already hashed.')
            )
