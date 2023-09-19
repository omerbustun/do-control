from django import forms
from .models import Configuration

class ConfigurationForm(forms.ModelForm):
    digitalocean_token = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DigitalOcean API Token'}))
    
    class Meta:
        model = Configuration
        fields = ['digitalocean_token']
