from django import forms
from .models import Configuration

class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = Configuration
        widgets = {
            'digitalocean_token': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'DigitalOcean API Token'}),

        }
        fields = '__all__'
