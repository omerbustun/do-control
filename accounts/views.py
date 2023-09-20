from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.contrib import messages

class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, f"{request.user} logged out.")
        return super().dispatch(request, *args, **kwargs)

@login_required
def home_view(request):
    return render(request, 'dashboard.html')

def base_view(request):
    return render(request, 'base.html')

def profile_view(request):
    return render(request, 'profile.html')