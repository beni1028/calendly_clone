from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from accounts.models import Events

@receiver(pre_save, sender=Events)
def compre_objects(sender, instance, **kwargs):
    old_instance = sender.objects.get(pk=instance.pk)
    if instance.invitees != old_instance.invitees:
        new_emails = list(set(instance.invitees)-set(old_instance.invitees)) 
        send_booking_email(new_emails, instance.slug)
        return