from django.shortcuts import render, redirect
from .models import Configuration
from .forms import ConfigurationForm
from django.contrib import messages

def config_view(request):
    config, created = Configuration.objects.get_or_create(pk=1)
    token_placeholder = '*' * len(config.digitalocean_token) if config.digitalocean_token else ''
    if request.method == "POST":
        form = ConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuration saved successfully!")
            return redirect('config_view')
    else:
        if config.digitalocean_token:
            visible_chars = config.digitalocean_token[:9]
            masked_chars = '*' * (len(config.digitalocean_token) - 9)
            config.digitalocean_token = visible_chars + masked_chars
        form = ConfigurationForm(instance=config)
    return render(request, 'config.html', {'form': form, 'token_placeholder': token_placeholder})


