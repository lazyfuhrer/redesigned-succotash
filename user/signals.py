# code
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_atlasid(sender, instance, created, **kwargs):
    if instance.atlas_id is None and instance.id is not None:
        instance.atlas_id = f"{settings.PREFIX_ATLAS_ID}{instance.id}"
        instance.save()
