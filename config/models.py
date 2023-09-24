from django.db import models


# For keeping the configuration in the DB.
class Configuration(models.Model):
    digitalocean_token = models.CharField(max_length=200, null=True, blank=True)
