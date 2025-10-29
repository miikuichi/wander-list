from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def reminders_page(request):
    """Reminders and Notifications landing page.

    Renders a basic template. Replace later with form handling and listings.
    Template path: templates/reminders/reminders.html
    """
    context = {}
    return render(request, "reminders/reminders.html", context)
