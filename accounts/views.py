from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from notifications.models import Notification
from django.shortcuts import redirect

class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, f"{request.user} logged out.")
        return super().dispatch(request, *args, **kwargs)

@login_required
def home_view(request):
    latest_notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')[:5]
    return render(request, 'dashboard.html', {'latest_notifications': latest_notifications})

def base_view(request):
    return render(request, 'base.html')

def profile_view(request):
    return render(request, 'profile.html')

# Notifications
def all_notifications(request):
    all_notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')
    return render(request, 'all_notifications.html', {'all_notifications': all_notifications})

def mark_notification_as_read(request, notification_id):
    notification = Notification.objects.get(id=notification_id, recipient=request.user)
    notification.mark_as_read()
    return redirect('all_notifications')
