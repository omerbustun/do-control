from django.shortcuts import render, redirect
from .models import Configuration
from .forms import ConfigurationForm
from django.contrib import messages

def config_view(request):
    config, created = Configuration.objects.get_or_create(pk=1)
    if request.method == "POST":
        form = ConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuration saved successfully!")
    else:
        form = ConfigurationForm(instance=config)
    return render(request, 'config.html', {'form': form})

