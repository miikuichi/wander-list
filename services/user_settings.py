# services/user_settings.py

from decimal import Decimal
from django.utils import timezone

TABLE = "user_settings"


def get_monthly_allowance(supabase, user_id):
    """
    Returns Decimal monthly allowance or None if not set.
    """
    try:
        res = supabase.table(TABLE).select("monthly_allowance").eq("user_id", user_id).single().execute()
    except Exception:
        # If the Supabase client throws, treat as 'not found' here and let caller log if needed
        return None

    data = getattr(res, "data", None)
    if not data:
        return None

    val = data.get("monthly_allowance")
    if val is None:
        return None

    # Convert to Decimal safely
    try:
        return Decimal(str(val))
    except Exception:
        return None


def set_monthly_allowance(supabase, user_id, value):
    """
    Upserts the monthly allowance for a user.
    """
    # Coerce Decimal or numeric-like input to float for Supabase client
    try:
        monthly = float(value)
    except Exception:
        monthly = None

    payload = {
        "user_id": user_id,
        "monthly_allowance": monthly,
        "updated_at": timezone.now().isoformat()
    }

    # Upsert (insert or update) on user_id
    return supabase.table(TABLE).upsert(payload, on_conflict="user_id").execute()
