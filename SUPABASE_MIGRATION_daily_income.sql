-- Migration: Create daily_income table for wallet balance feature
-- Date: November 19, 2025
-- Description: Tracks extra income (tips, gifts, side hustles) that adds to daily wallet balance

CREATE TABLE IF NOT EXISTS daily_income (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES login_user(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    source VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster queries by user and date
CREATE INDEX idx_daily_income_user_date ON daily_income(user_id, date);

-- Create index for user queries
CREATE INDEX idx_daily_income_user ON daily_income(user_id);

-- Add comment to table
COMMENT ON TABLE daily_income IS 'Tracks extra income that adds to users daily wallet balance with carryover';

-- Add comments to columns
COMMENT ON COLUMN daily_income.user_id IS 'Reference to login_user table';
COMMENT ON COLUMN daily_income.amount IS 'Income amount in pesos (must be positive)';
COMMENT ON COLUMN daily_income.source IS 'Source of income: Work Tip, Gift, Side Hustle, Allowance Advance, Savings Withdrawal, Other';
COMMENT ON COLUMN daily_income.date IS 'Date when income was received';
COMMENT ON COLUMN daily_income.notes IS 'Optional notes about the income';

-- Success message
SELECT 'daily_income table created successfully!' AS message;
