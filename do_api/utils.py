from config.models import Configuration
import digitalocean

def create_droplet(manager, name, region, snapshot_image_id, snapshot_size):
    token = Configuration.objects.first().digitalocean_token
    keys = manager.get_all_sshkeys()
    droplet = digitalocean.Droplet(token=token,
                                   name=name,
                                   region=region,
                                   image=snapshot_image_id,
                                   size_slug=snapshot_size,
                                   backups=False,
                                   ssh_keys=keys,
                                   monitoring=True)
    droplet.create()
    return droplet