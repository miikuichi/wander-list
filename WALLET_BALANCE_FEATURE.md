# 💰 Wallet Balance Feature with Carryover

## Overview
Implemented a complete wallet balance system that tracks daily allowance + extra income with **carryover functionality**. Money left over from one day carries forward to the next day, simulating a real wallet.

---

## 🎯 Feature Specifications

### **Option B: Rolling Balance (Implemented)**
- Opening balance from yesterday
- Daily allowance from monthly allowance
- Extra income (tips, gifts, etc.)
- Expenses deducted
- Closing balance carries to next day

### **Option A: Separate from Monthly Allowance (Implemented)**
- Extra income doesn't affect monthly allowance calculation
- Monthly allowance remains fixed (₱2,000)
- Income is tracked separately and independently

---

## 📊 How It Works

### **Daily Calculation Formula:**
```
Opening Balance (from yesterday)
+ Daily Allowance (monthly ÷ days_in_month)
+ Extra Income (today)
- Expenses (today)
= Closing Balance (carries to tomorrow)
```

### **Example Scenario:**

**November 19:**
- Opening: ₱0 (first day)
- Daily Allowance: ₱66.67
- Income: ₱500 (work tip)
- Expenses: ₱100
- **Closing: ₱466.67** ✅

**November 20:**
- **Opening: ₱466.67** (carried from Nov 19)
- Daily Allowance: ₱66.67
- Income: ₱0
- Expenses: ₱50
- **Closing: ₱483.34** ✅

**November 21:**
- **Opening: ₱483.34** (carried from Nov 20)
- Daily Allowance: ₱66.67
- Income: ₱200 (side hustle)
- Expenses: ₱150
- **Closing: ₱600.01** ✅

---

## 🗄️ Database Schema

### **New Table: `daily_income`**
```sql
CREATE TABLE daily_income (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES login_user(id),
    amount NUMERIC(12, 2) NOT NULL,
    source VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### **Income Sources:**
1. Work Tip
2. Gift
3. Side Hustle
4. Allowance Advance
5. Savings Withdrawal
6. Other

---

## 📝 Implementation Details

### **New Function: `get_wallet_balance(user_id)`**
**Location:** `expenses/views.py`

**Returns:**
- `opening_balance`: Carried from yesterday
- `daily_allowance`: Today's base allowance
- `daily_income`: Extra income added today
- `today_expenses`: Total spent today
- `total_available`: Opening + Allowance + Income
- `closing_balance`: Remaining (carries to tomorrow)
- `percent_used`: Percentage of total available spent

**Logic:**
1. Calculate today's daily allowance from monthly allowance
2. Calculate yesterday's closing balance:
   - Yesterday's allowance + Yesterday's income - Yesterday's expenses
3. Get today's extra income from `daily_income` table
4. Get today's expenses from `expenses` table
5. Calculate totals and percentages

---

### **New View: `add_income_view(request)`**
**Location:** `expenses/views.py`
**URL:** `/expenses/add-income/`

**Functionality:**
- Handles POST requests to add extra income
- Validates amount, source, date
- Inserts into `daily_income` table
- Redirects to expenses page with success message

**Validations:**
- ✅ Amount must be positive
- ✅ Amount < ₱999,999,999.99
- ✅ Source must be from predefined list
- ✅ Date must be valid format
- ✅ Cannot select future dates

---

## 🎨 User Interface

### **Wallet Balance Summary Card**
**Location:** Top of expenses page

**Displays:**
- Opening Balance (carried from yesterday)
- Daily Allowance (today's base budget)
- Extra Income (tips, gifts, etc.)
- Total Available
- Spent Today
- Remaining (carries to tomorrow)
- Percentage used

**Visual Design:**
- Gradient purple background
- White text
- Clear hierarchy
- Real-time calculations

---

### **Add Income Form**
**Location:** Right side of expenses page (alongside Add Expense)

**Fields:**
1. **Amount** (₱, required, min: 0.01)
2. **Source** (dropdown, required)
   - Work Tip
   - Gift
   - Side Hustle
   - Allowance Advance
   - Savings Withdrawal
   - Other
3. **Date** (auto-fills today, editable, cannot be future)
4. **Notes** (optional, textarea)

**Buttons:**
- Clear Form (reset)
- Add Income (submit, green button)

---

## 🔧 Updated Components

### **`expenses_view` (Modified)**
- Now uses `get_wallet_balance()` instead of `get_daily_allowance_remaining()`
- Passes `wallet` object to template
- Includes `income_sources` in context

### **`expenses.html` Template (Enhanced)**
- Added wallet balance summary card
- Split expense/income forms side-by-side
- Two-column layout using Bootstrap grid
- Moved recent expenses below forms

### **`expenses/urls.py` (Added)**
```python
path('add-income/', views.add_income_view, name='add_income'),
```

---

## 📦 Files Modified

### **Backend:**
1. `expenses/views.py`
   - Added `INCOME_SOURCES` constant
   - Added `get_wallet_balance()` function
   - Added `add_income_view()` function
   - Modified `expenses_view()` to use wallet balance
   - Added `timedelta` import

2. `expenses/urls.py`
   - Added `/add-income/` route

### **Frontend:**
3. `templates/expenses/expenses.html`
   - Added wallet balance summary card
   - Added Add Income form
   - Restructured layout (2-column grid)
   - Enhanced visual design

### **Database:**
4. `SUPABASE_MIGRATION_daily_income.sql`
   - SQL script to create `daily_income` table
   - Includes indexes and comments

---

## 🚀 Setup Instructions

### **Step 1: Run SQL Migration**
Execute the SQL file in Supabase SQL Editor:
```bash
# File: SUPABASE_MIGRATION_daily_income.sql
# Location: Project root directory
```

1. Open Supabase Dashboard
2. Go to SQL Editor
3. Paste contents of `SUPABASE_MIGRATION_daily_income.sql`
4. Run the script
5. Verify table creation: `SELECT * FROM daily_income;`

### **Step 2: Test the Feature**
1. Navigate to `/expenses/`
2. View wallet balance summary (should show ₱66.67 allowance)
3. Add income: ₱500 work tip for today
4. Wallet balance should update: ₱566.67 total available
5. Add expense: ₱100
6. Closing balance: ₱466.67
7. **Next day:** Opening balance should be ₱466.67 ✅

---

## 🧪 Testing Scenarios

### **Scenario 1: Basic Income Addition**
```
Action: Add ₱500 work tip today
Expected:
- Daily Income: ₱500.00
- Total Available: ₱66.67 + ₱500 = ₱566.67
- Success message: "Income of ₱500.00 (Work Tip) added successfully!"
```

### **Scenario 2: Carryover to Next Day**
```
Day 1:
- Allowance: ₱66.67
- Income: ₱500
- Expenses: ₱100
- Closing: ₱466.67

Day 2 (automatic):
- Opening: ₱466.67 ← Carried from Day 1
- Allowance: ₱66.67
- Total Available: ₱533.34
```

### **Scenario 3: Multiple Income Sources**
```
Action: Add ₱300 Gift + ₱200 Side Hustle
Expected:
- Daily Income: ₱500.00 (sum of both)
- Total Available: ₱66.67 + ₱500 = ₱566.67
```

### **Scenario 4: Negative Balance (Overspending)**
```
Day 1:
- Allowance: ₱66.67
- Income: ₱0
- Expenses: ₱200
- Closing: -₱133.33

Day 2:
- Opening: ₱0.00 ← Cannot be negative (max with 0)
- Allowance: ₱66.67
- Need to add income or reduce spending
```

---

## 🎯 Key Benefits

### **1. Realistic Wallet Simulation**
- Money carries over day-to-day
- Matches real-world behavior
- Can save up for larger purchases

### **2. Flexible Income Tracking**
- Log tips, gifts, side hustles
- Separate from regular allowance
- Clear source categorization

### **3. Accurate Budget Awareness**
- See total available money
- Opening + Allowance + Income
- Know exactly how much you can spend

### **4. Better Financial Planning**
- Yesterday's savings = today's opening balance
- Encourages saving for future days
- Visualize spending trends

---

## 📊 Notification Integration

### **Updated Daily Allowance Notification**
- Triggers at 80% of **total available** (not just allowance)
- Considers: Opening Balance + Allowance + Income
- Prevents false alerts when extra income is available

**Example:**
```
Total Available: ₱566.67
Spent: ₱470.00 (83%)
→ Notification: "Daily Allowance Alert: 83% Used"
```

---

## 🔮 Future Enhancements (Optional)

### **Income History View**
- Dedicated page showing all income entries
- Filter by source, date range
- Total income per month/week

### **Wallet Balance Chart**
- Line graph showing balance over time
- Identify spending patterns
- Highlight income spikes

### **Monthly Carryover**
- Option to reset balance at month start
- Or continue carrying across months
- User preference setting

### **Income Categories**
- Subcategories for sources (e.g., "Work Tip → Restaurant")
- Better tracking of income streams
- Analytics per category

---

## 📞 Support

### **Common Issues:**

**Q: Opening balance is ₱0 every day?**
A: Make sure `daily_income` table exists in Supabase. Run migration SQL.

**Q: Income not showing in wallet balance?**
A: Check that income date matches expense date. Use today's date.

**Q: Carryover not working?**
A: Function calculates yesterday's balance automatically. Ensure dates are sequential.

**Q: Can balance go negative?**
A: Opening balance uses `max(balance, 0)` so it floors at ₱0.

---

## ✅ Implementation Checklist

- [x] Create `daily_income` table schema
- [x] Add `INCOME_SOURCES` constant
- [x] Implement `get_wallet_balance()` function
- [x] Implement `add_income_view()` function
- [x] Update `expenses_view()` to use wallet balance
- [x] Add `/add-income/` URL route
- [x] Design wallet balance summary card
- [x] Create Add Income form UI
- [x] Update notification logic for total available
- [x] Add carryover calculation logic
- [x] Write SQL migration file
- [x] Create documentation

---

## 🎉 Feature Complete!

The wallet balance system with carryover is now fully implemented. Users can:
- Track daily allowance automatically
- Log extra income (tips, gifts, side hustles)
- See money carry over day-to-day
- View comprehensive wallet balance summary
- Get notified when approaching spending limits

**Next Step:** Run the SQL migration in Supabase to create the `daily_income` table, then test the feature!
