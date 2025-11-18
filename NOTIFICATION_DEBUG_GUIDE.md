# Budget Alert & Notification Troubleshooting Guide

## Critical Fixes Applied ✅

### **Fix 1: Database Query Bug**
The `get_category_budget_status()` function was trying to join with a non-existent `budget_categories` table. The schema has been simplified to store categories directly in the `budget_alerts` table as strings.

**Fixed in `expenses/views.py`:**
```python
# OLD (BROKEN):
alert_response = supabase.table('budget_alerts')\
    .select('*, budget_categories!inner(*)')\
    .eq('budget_categories.name', category_name)\

# NEW (WORKING):
alert_response = supabase.table('budget_alerts')\
    .select('*')\
    .eq('category', category_name)\
```

### **Fix 2: Removed Floating Banner Alerts** 
Budget alerts were showing as floating Django messages instead of appearing in the notification bell. The code was using both `messages.warning()` (floating banners) AND the notification system.

**Fixed in `expenses/views.py`:**
- ❌ Removed Django warning messages for budget threshold alerts
- ❌ Removed Django warning messages for daily allowance alerts  
- ✅ Budget alerts NOW ONLY appear in the notification bell (top-right icon with red badge)
- ✅ Kept error messages that block expenses (e.g., budget exceeded)

## Testing Checklist

### 1. **Verify Budget Alert Creation**
1. Go to: http://127.0.0.1:8000/budget-alerts/
2. Create a new budget alert:
   - Category: Food
   - Budget Limit: ₱100.00
   - Threshold: 80%
   - Enable "Notification Bell" ✓
   - Enable "Email Notification" ✓
3. Click "Create Budget Alert"
4. You should see: "✅ Budget alert created for 'Food' (₱100.00)!"

### 2. **Trigger Budget Alert**
1. Go to: http://127.0.0.1:8000/expenses/
2. Add an expense:
   - Amount: ₱85.00
   - Category: Food
   - Date: Today
3. Check the browser console (F12) for logs
4. Expected logs:
   ```
   Checking budget alerts after expense: user=X, category=Food, amount=85
   Budget status: 85.0% used (threshold: 80%)
   Sending budget alert notification: 85.0% >= 80%
   Budget alert notification result: {...}
   ```

### 3. **Check Notification Bell**
1. Look at the top-right notification bell icon
2. Should show a red badge with number: "1"
3. Click the bell icon
4. Should see: "💰 Budget Alert: Food"
5. Message: "Budget threshold reached (80%)"

### 4. **Check Email Notification**
**Prerequisites:**
- Gmail account configured in `.env` file
- `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` set

**Test:**
1. Go to: http://127.0.0.1:8000/notifications/
2. Click "Send Test Email" button
3. Check your inbox (and spam folder)
4. Should receive: "💰 PisoHeroes Email Test"

**If email fails:**
- Check `.env` file has correct credentials
- Verify Gmail App Password is generated (not regular password)
- Check terminal for error messages
- Try console backend for testing (see below)

### 5. **Check Daily Allowance Alert**
1. Set monthly allowance: http://127.0.0.1:8000/expenses/
2. Add multiple expenses until total > 80% of daily allowance
3. Should trigger: "💰 Daily Allowance Alert: XX% Used"

## Common Issues & Solutions

### Issue 1: No Notifications Appearing
**Symptoms:** No badge on bell icon, empty notification dropdown

**Check:**
```bash
# In terminal running Django server, look for:
"Checking budget alerts after expense: user=X, category=Food"
"Budget status: X% used (threshold: Y%)"
```

**Solutions:**
1. Verify budget alert exists and is **active**
2. Check category name matches exactly (case-sensitive)
3. Check threshold is reached (e.g., 85% spent >= 80% threshold)
4. Check expense date is today (for immediate alerts)

### Issue 2: Email Not Sending
**Symptoms:** Dashboard notification works but no email

**Check Terminal for Errors:**
```
Failed to send email to user@email.com: [Errno 111] Connection refused
SMTPAuthenticationError: (535, 'Authentication failed')
```

**Solutions:**

**Option A: Use Console Backend (Testing Only)**
Edit `wander_list/settings.py`:
```python
# Comment out SMTP backend
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Use console backend instead (emails print to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

**Option B: Fix Gmail Configuration**
1. Create Gmail App Password:
   - Go to: https://myaccount.google.com/apppasswords
   - Generate 16-character password
2. Update `.env`:
   ```
   EMAIL_HOST_USER=your.email@gmail.com
   EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop
   ```
3. Restart Django server

### Issue 3: Budget Alert Not Triggering
**Symptoms:** Expense added but no notification

**Debugging Steps:**

1. **Check if budget alert exists:**
   ```bash
   # Open Django shell
   python manage.py shell
   ```
   ```python
   from supabase_service import get_service_client
   supabase = get_service_client()
   
   # Replace 4 with your user_id
   alerts = supabase.table('budget_alerts').select('*').eq('user_id', 4).eq('active', True).execute()
   print(alerts.data)
   ```

2. **Check category spelling:**
   - Budget alert: "Food"
   - Expense: "Food"
   - Must match EXACTLY (case-sensitive)

3. **Check threshold logic:**
   - If threshold is 80% and you've spent 79%, NO alert
   - If threshold is 80% and you've spent 80%, ALERT ✓
   - If threshold is 80% and you've spent 85%, ALERT ✓

4. **Check for duplicate notifications:**
   - Only ONE notification per day per category
   - If alert already sent today, won't send again
   - Wait until tomorrow or delete old notifications

### Issue 4: Notification Bell Not Loading
**Symptoms:** Bell icon shows "Loading..." forever

**Check Browser Console (F12):**
```
Error loading notifications: Failed to fetch
```

**Solutions:**
1. Verify you're logged in
2. Check URL is correct: `/notifications/api/recent/`
3. Check Django server is running
4. Check for JavaScript errors in console

## Database Verification

### Check Notification Logs in Django Admin
1. Add to `notifications/admin.py` if not already there:
   ```python
   from django.contrib import admin
   from .models import NotificationLog
   
   @admin.register(NotificationLog)
   class NotificationLogAdmin(admin.ModelAdmin):
       list_display = ['id', 'user_id', 'title', 'category', 'notification_type', 'status', 'created_at']
       list_filter = ['notification_type', 'category', 'status', 'created_at']
       search_fields = ['title', 'message']
   ```

2. Access admin: http://127.0.0.1:8000/admin/
3. View "Notification logs" to see all notifications

### Check Budget Alerts in Supabase
1. Go to: https://supabase.com/dashboard
2. Select your project
3. Click "Table Editor"
4. Open `budget_alerts` table
5. Verify:
   - `user_id` matches your session user
   - `category` matches exactly (e.g., "Food")
   - `active` is `true`
   - `threshold_percent` is reasonable (e.g., 80)
   - `amount_limit` is set (e.g., 100.00)

## Enhanced Logging

The fix includes additional logging in `expenses/views.py` that will help debug issues:

```python
logger.info(f"Checking budget alerts after expense: user={user_id}, category={category}, amount={amount}")
logger.info(f"Budget status: {percentage:.1f}% used (threshold: {threshold}%)")
logger.info(f"Sending budget alert notification: {percentage:.1f}% >= {threshold}%")
logger.info(f"Budget alert notification result: {result}")
```

**To see these logs:**
1. Terminal running Django server shows INFO level logs
2. Look for lines starting with "Checking budget alerts"
3. Follow the flow to see where it fails

## Quick Test Script

Run this in Django shell to manually test notification system:

```python
from notifications.services import NotificationService

# Replace with your user_id and email
user_id = 4
user_email = "your.email@gmail.com"

# Send test notification
result = NotificationService.create_budget_alert_notification(
    user_id=user_id,
    category="Food",
    spent=85.00,
    limit=100.00,
    percentage=85.0,
    threshold=80,
    user_email=user_email,
)

print("Result:", result)
print("Dashboard notification:", result.get('dashboard'))
print("Email notification:", result.get('email'))
```

## Expected Behavior

### When Budget Alert Triggers:
1. **Immediate** (within 1 second):
   - Dashboard notification created in SQLite `notification_logs`
   - Notification badge appears on bell icon
   - Dropdown shows new notification

2. **Within 5-10 seconds**:
   - Email sent via Gmail SMTP (if configured)
   - Email appears in inbox
   - Push notification sent (if FCM configured)

3. **On Next Page Load**:
   - Notification bell badge updates
   - Can click notification to mark as read
   - Can view all notifications at `/notifications/`

## Still Not Working?

### Collect Debug Information:
1. Django server terminal output
2. Browser console output (F12)
3. Budget alert details (category, threshold, limit)
4. User ID from session
5. Email configuration status

### Share This:
```bash
# In Django shell
from supabase_service import get_service_client
from notifications.models import NotificationLog

user_id = 4  # Your user_id

# Check budget alerts
supabase = get_service_client()
alerts = supabase.table('budget_alerts').select('*').eq('user_id', user_id).execute()
print("Budget Alerts:", alerts.data)

# Check notification logs
notifications = NotificationLog.objects.filter(user_id=user_id).order_by('-created_at')[:10]
for n in notifications:
    print(f"[{n.notification_type}] {n.title} - {n.status} - {n.created_at}")
```

## Next Steps

1. ✅ **Fix Applied** - Budget alert querying fixed
2. 🧪 **Test** - Follow testing checklist above
3. 📧 **Email** - Configure Gmail or use console backend
4. 📊 **Monitor** - Watch terminal logs when adding expenses
5. 🔔 **Verify** - Check notification bell and dropdown

The main issue preventing budget alerts from working has been fixed. Follow the testing steps above to verify everything is working correctly!
