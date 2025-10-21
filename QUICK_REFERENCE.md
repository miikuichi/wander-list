# 📋 Quick Reference: Simplified Supabase Schema# 🚀 Quick Reference Card - Wander List

## 🎯 What Changed## One-Page Cheat Sheet for All Features

### **From Complex to Simple**---

| Before (Complex) | After (Simplified) |## 🔐 Google OAuth Quick Test

|-----------------|-------------------|

| 7+ tables | 5 tables |```bash

| Separate `budget_categories` table | Category as VARCHAR in `budget_alerts` |# 1. Start server

| New `users` table | Use existing `login_user` table |python manage.py runserver

| Complex FK relationships | Simple, direct relationships |

| JOIN queries for categories | Direct column access |# 2. Open browser

http://localhost:8000/login/

---

# 3. Click "Sign in with Google"

## 📊 Final Database Schema

# 4. Expected: Redirects to Google → Back to dashboard

````

5 TABLES:

**Not working?** Check: `GOOGLE_OAUTH_SETUP.md`

1. login_user (existing + daily_allowance)

   ├── id (PK)---

   ├── username

   ├── email## 🧪 Run Tests Quick Command

   ├── password

   └── daily_allowance ⭐ NEW```bash

# All tests

2. expenses (existing)python run_tests.py

   ├── id (PK)

   ├── user_id (FK → login_user.id)# Just expenses

   ├── amountpython manage.py test expenses

   ├── category (VARCHAR) ⭐ NOT FK

   ├── date# Verbose

   └── notespython run_tests.py --verbose

```

3. budget_alerts (SIMPLIFIED)

   ├── id (PK)**Tests failing?** Check: `expenses/tests.py` for test names

   ├── user_id (FK → login_user.id)

   ├── category (VARCHAR) ⭐ NOT FK---

   ├── amount_limit

   ├── threshold_percent## ✅ Acceptance Criteria (Flags) Template

   ├── notify_dashboard

   ├── notify_email```

   ├── notify_pushUser Story: [Feature Name]

   └── active

As a [user type]

4. savings_goalsI want [goal]

   ├── id (PK)So that [benefit]

   ├── user_id (FK → login_user.id)

   ├── nameFlags (Must ALL be ✅ before "Done"):

   ├── target_amount☐ [Specific, testable criterion 1]

   ├── current_amount☐ [Specific, testable criterion 2]

   ├── description☐ [Specific, testable criterion 3]

   ├── target_date```

   ├── status

   └── completed_at**Example**: See `SPRINT_CHECKLIST.md` → "Feature: Google OAuth Sign-In"



5. savings_transactions (optional)---

   ├── id (PK)

   ├── goal_id (FK → savings_goals.id)## 🔍 Expense Validation Rules

   ├── amount

   ├── transaction_type| Input                             | Result                         |

   └── notes| --------------------------------- | ------------------------------ |

```| Amount: `-50`                     | ❌ "Must be greater than zero" |

| Amount: `0`                       | ❌ "Must be greater than zero" |

---| Amount: `abc`                     | ❌ "Must be a valid number"    |

| Amount: `999999999999`            | ❌ "Amount too large"          |

## 🚀 Quick Start Commands| Category: `Hacking`               | ❌ "Invalid category"          |

| Date: `15-10-2025`                | ❌ "Invalid date format"       |

### **1. Run SQL Setup**| Amount: `50.75`, Category: `Food` | ✅ Success!                    |



```sql---

-- In Supabase SQL Editor, run:

\i SUPABASE_SQL_SIMPLIFIED.sql## 📊 Budget Alert Logic

```

```python

Or copy-paste the entire file.# How alerts are triggered:

percent_spent = (actual_expenses / budget_limit) × 100

### **2. Verify Tables**

if percent_spent >= threshold_percent:

```sql    → Trigger Alert! 🚨

SELECT table_name FROM information_schema.tables

WHERE table_schema = 'public' # Example:

  AND table_name IN ('login_user', 'expenses', 'budget_alerts', 'savings_goals')# Budget: ₱3000, Threshold: 55%

ORDER BY table_name;# Spent: ₱1800

```# Calculation: (1800 / 3000) × 100 = 60%

# Result: 60% >= 55% ✅ ALERT TRIGGERED

### **3. Test with Sample Data**```



```sql**Color codes**:

-- Add daily allowance to user

UPDATE login_user SET daily_allowance = 500.00 WHERE id = YOUR_USER_ID;- 🟡 Yellow: Threshold reached (< 100%)

- 🔴 Red: Budget exceeded (≥ 100%)

-- Create budget alert (SIMPLIFIED - direct category)

INSERT INTO budget_alerts (user_id, category, amount_limit, threshold_percent, active)---

VALUES (YOUR_USER_ID, 'Food', 2000.00, 80, TRUE);

## 🗂️ File Structure Reference

-- Add expense

INSERT INTO expenses (user_id, amount, category, date, notes)```

VALUES (YOUR_USER_ID, 150.00, 'Food', CURRENT_DATE, 'Lunch');wander-list/

├── login/

-- Check daily allowance│   ├── views.py              # OAuth: google_login(), oauth_callback()

SELECT * FROM get_daily_allowance_remaining(YOUR_USER_ID);│   ├── urls.py               # Routes: /google/, /callback/

│   └── templates/

-- Check budget status│       └── login/

SELECT * FROM get_category_budget_status(YOUR_USER_ID, 'Food');│           ├── login.html    # Google button added

```│           └── oauth_callback.html  # Token handler

├── expenses/

---│   ├── views.py              # Validation: 6 checks added

│   ├── tests.py              # Test suite: 12 tests

## 💻 Django Code Examples│   └── templates/

│       └── expenses/

### **Create Budget Alert**│           └── expenses.html # Client-side validation

├── dashboard/

```python│   ├── views.py              # Alert calculation logic

from supabase_service import get_service_client│   └── templates/

│       └── dashboard/

supabase = get_service_client()│           └── dashboard.html # Alert display

├── GOOGLE_OAUTH_SETUP.md     # OAuth setup guide (75 steps)

# SIMPLIFIED - No category table needed!├── SPRINT_CHECKLIST.md       # Sprint templates & flags

supabase.table('budget_alerts').insert({├── IMPLEMENTATION_SUMMARY.md # This document

    'user_id': request.session['user_id'],└── run_tests.py              # Quick test runner

    'category': 'Food',  # ⭐ Direct column```

    'amount_limit': 2000.00,

    'threshold_percent': 80,---

    'active': True

}).execute()## ⚡ Common Commands

```

```bash

### **Get User's Alerts**# Development

python manage.py runserver          # Start server

```pythonpython manage.py makemigrations     # Create migrations

# SIMPLIFIED - No JOIN needed!python manage.py migrate            # Apply migrations

alerts = supabase.table('budget_alerts')\python manage.py shell              # Django shell

    .select('*')\

    .eq('user_id', user_id)\# Testing

    .eq('active', True)\python manage.py test               # Run all tests

    .execute()python manage.py test expenses      # Test one app

python run_tests.py --verbose       # Verbose tests

for alert in alerts.data:

    print(alert['category'])  # ⭐ Direct access# Database

```python manage.py dbshell            # SQLite shell

python manage.py flush              # Clear database

### **Check Daily Allowance**

# Static files

```pythonpython manage.py collectstatic      # Gather static files

from decimal import Decimal```

from datetime import date

---

# Get user's daily allowance

user = supabase.table('login_user')\## 🐛 Quick Troubleshooting

    .select('daily_allowance')\

    .eq('id', user_id)\| Problem                   | Solution                         |

    .single()\| ------------------------- | -------------------------------- |

    .execute()| OAuth redirect error      | Check Google Cloud Console URIs  |

| Tests fail on import      | Run from project root directory  |

daily_allowance = Decimal(str(user.data['daily_allowance']))| Validation not working    | Check both client & server-side  |

| Alerts not showing        | Verify user_id in session        |

# Get today's expenses| Supabase connection error | Check .env file has correct keys |

today = date.today().isoformat()

expenses = supabase.table('expenses')\---

    .select('amount')\

    .eq('user_id', user_id)\## 📝 Sprint Workflow (5 Steps)

    .eq('date', today)\

    .execute()```

1. START SPRINT

today_spending = sum(Decimal(str(exp['amount'])) for exp in expenses.data)   ├─ Copy SPRINT_CHECKLIST.md → SPRINT_01.md

remaining = daily_allowance - today_spending   └─ Fill in sprint goal & dates



# Block if exceeds2. WRITE USER STORIES

if expense_amount > remaining:   ├─ Use template from checklist

    raise ValidationError("Daily allowance exceeded!")   └─ Define clear acceptance criteria (flags)

```

3. DEVELOP FEATURES

---   ├─ Code feature

   ├─ Write tests

## 📁 Files Created/Updated   ├─ Check off flags ✅

   └─ Code review

### **New Files**

✅ `SUPABASE_SQL_SIMPLIFIED.sql` - Complete SQL setup (simplified schema)  4. TEST EVERYTHING

✅ `SUPABASE_IMPLEMENTATION_GUIDE.md` - Step-by-step setup guide     ├─ Unit tests pass

✅ `MIGRATION_PLAN.md` - Data migration instructions     ├─ Integration tests pass

✅ `QUICK_REFERENCE.md` - This file     ├─ Manual testing complete

   └─ Edge cases verified

### **Updated Files**

✅ `budget_alerts/views.py` - Uses simplified schema (no category FK)  5. END SPRINT

✅ `budget_alerts/forms.py` - Category normalization + duplicate checking     ├─ Complete retrospective

✅ `expenses/views.py` - Daily allowance + category budget checking     ├─ Calculate velocity

✅ `login/models.py` - Added daily_allowance field     └─ Plan next sprint

```

---

---

## ✨ Key Features

## 🎯 Definition of "Done"

### **1. Category Normalization**

Feature is ✅ DONE when:

User enters → System stores:

- "foods" → "Food"1. Code written & committed

- "transportation" → "Transport"2. All flags checked ✅

- "school stuff" → "School Supplies"3. Tests pass

- "gaming" → "Gaming" (custom)4. Code reviewed

5. Documentation updated

### **2. Daily Allowance Enforcement**6. Manual testing complete

7. No known bugs

```python8. Demo ready

# Automatically blocks expenses exceeding daily allowance

if expense_amount > remaining_daily_allowance:**Not done if ANY item unchecked!**

    return "Daily Allowance Exceeded!"

```---



### **3. Category Budget Enforcement**## 📞 Quick Help



```python| Need help with...  | Check this file...          |

# Blocks expenses exceeding category budget| ------------------ | --------------------------- |

if category_total + expense_amount > category_limit:| Google OAuth setup | `GOOGLE_OAUTH_SETUP.md`     |

    return "Category Budget Exceeded!"| Running tests      | `run_tests.py --help`       |

```| Sprint planning    | `SPRINT_CHECKLIST.md`       |

| All three features | `IMPLEMENTATION_SUMMARY.md` |

### **4. Duplicate Prevention**| Expense validation | `expenses/tests.py`         |

| Budget alerts      | `dashboard/views.py`        |

```python

# Prevents creating duplicate active alerts for same category---

# Only ONE active alert per user per category allowed

```## 🔗 Important URLs (Local Development)



---```

Login:            http://localhost:8000/login/

## 🧪 Testing ChecklistRegister:         http://localhost:8000/login/register/

Dashboard:        http://localhost:8000/dashboard/

- [ ] SQL script runs without errorsExpenses:         http://localhost:8000/expenses/

- [ ] All 5 tables createdBudget Alerts:    http://localhost:8000/budget-alerts/

- [ ] Helper functions createdOAuth Callback:   http://localhost:8000/login/callback/

- [ ] Budget alert CRUD worksLogout:           http://localhost:8000/login/exit/

- [ ] Category normalization works```

- [ ] Duplicate prevention works

- [ ] Daily allowance check works---

- [ ] Category budget check works

- [ ] Savings goals work (if migrated)## 🎓 Key Concepts

- [ ] Dashboard shows real data

**Acceptance Criteria (Flags)**: Specific conditions that must be met for a feature to be "done"

---

**OAuth Flow**: Third-party authentication (Google → Supabase → Django → User logged in)

## 🔧 Environment Variables

**Server-side Validation**: Checking data in Python (can't be bypassed)

Make sure `.env` has:

**Client-side Validation**: Checking data in browser (for UX, not security)

```env

SUPABASE_URL=https://your-project.supabase.co**Budget Alert Threshold**: Percentage at which alert triggers (e.g., 80% of budget)

SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

```**Sprint Velocity**: Completed story points ÷ Planned story points × 100%



------



## 📞 Support## ✅ Pre-Demo Checklist



If you need help:```

☐ Server runs without errors

1. Check `SUPABASE_IMPLEMENTATION_GUIDE.md` for detailed steps☐ Can register new user

2. Check `MIGRATION_PLAN.md` for migration process☐ Can login with email/password

3. Check `TESTING_GUIDE.md` for testing procedures☐ Google OAuth button visible

4. Review Supabase Dashboard → Logs for errors☐ Can add expense (positive amount)

☐ Negative expense rejected

---☐ Budget alert visible on dashboard

☐ Alert shows correct percentage

## 🎉 Summary☐ Can create new budget alert

☐ Logout clears session

**What You Get:**☐ Tests pass (python run_tests.py)

- ✅ Simple 5-table schema```

- ✅ No complex relationships

- ✅ Category normalization**All checked?** Ready to demo! 🎉

- ✅ Daily allowance enforcement

- ✅ Category budget enforcement---

- ✅ Duplicate prevention

- ✅ Easy to understand**Print this page for quick reference during development!**

- ✅ Easy to maintain

---

**Total Implementation Time:** 80-120 minutes

Last Updated: October 15, 2025

**Complexity Level:** Low 🟢Project: Wander List (PisoHeroes)

Team: [Your Team Name]

---Sprint: 1


**Created:** October 22, 2025
**Schema:** Simplified v1.0
**Status:** Ready to Deploy 🚀
````
