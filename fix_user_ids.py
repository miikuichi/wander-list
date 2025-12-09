"""
Script to fix user ID mismatches between local SQLite and Supabase.
Run this to synchronize user IDs and verify database consistency.

Usage: python fix_user_ids.py
"""

import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wander_list.settings')
django.setup()

from login.models import User
from supabase_service import get_service_client

def check_and_fix_users():
    """Check for user ID mismatches and provide report."""
    
    print("\n" + "="*60)
    print("USER DATABASE VERIFICATION & SYNC REPORT")
    print("="*60 + "\n")
    
    supabase = get_service_client()
    
    # Get all users from Supabase
    print("📊 Fetching users from Supabase...")
    try:
        response = supabase.table('login_user').select('*').execute()
        supabase_users = {user['email']: user for user in response.data}
        print(f"✅ Found {len(supabase_users)} users in Supabase\n")
    except Exception as e:
        print(f"❌ Error fetching from Supabase: {e}")
        return
    
    # Get all users from local SQLite
    print("📊 Fetching users from local SQLite...")
    local_users = User.objects.all()
    print(f"✅ Found {local_users.count()} users in local database\n")
    
    print("-"*60)
    print("DETAILED USER ANALYSIS")
    print("-"*60 + "\n")
    
    issues_found = 0
    
    for local_user in local_users:
        email = local_user.email
        print(f"👤 User: {local_user.username} ({email})")
        print(f"   Local ID: {local_user.id}")
        
        if email in supabase_users:
            remote_user = supabase_users[email]
            remote_id = remote_user['id']
            print(f"   Remote ID: {remote_id}")
            
            if local_user.id != remote_id:
                print(f"   ⚠️  ID MISMATCH DETECTED!")
                print(f"   📝 This user will appear as ID {remote_id} when logged in")
                issues_found += 1
            else:
                print(f"   ✅ IDs match - OK")
        else:
            print(f"   ❌ NOT FOUND in Supabase database!")
            print(f"   📝 This user exists locally but not in Supabase")
            print(f"   🔧 Action needed: Re-register or manually add to Supabase")
            issues_found += 1
        
        print()
    
    # Check for users in Supabase but not locally
    print("-"*60)
    print("REVERSE CHECK: Supabase users not in local DB")
    print("-"*60 + "\n")
    
    local_emails = set(user.email for user in local_users)
    missing_locally = []
    
    for email, remote_user in supabase_users.items():
        if email not in local_emails:
            missing_locally.append(remote_user)
            print(f"👤 User: {remote_user['username']} ({email})")
            print(f"   Remote ID: {remote_user['id']}")
            print(f"   ⚠️  EXISTS in Supabase but NOT in local database")
            print(f"   📝 Will be created locally on next login")
            print()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Local users: {local_users.count()}")
    print(f"Supabase users: {len(supabase_users)}")
    print(f"ID mismatches: {issues_found}")
    print(f"Missing locally: {len(missing_locally)}")
    
    if issues_found > 0 or len(missing_locally) > 0:
        print("\n⚠️  ACTION REQUIRED:")
        print("   - Users with ID mismatches should re-login to sync properly")
        print("   - The system now uses Supabase IDs as the source of truth")
        print("   - Local IDs are kept for admin dashboard display only")
    else:
        print("\n✅ All users are properly synchronized!")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    check_and_fix_users()
