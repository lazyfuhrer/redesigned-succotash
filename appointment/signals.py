from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from appointment.models import Appointment
from base.utils import send_appointment_cancelled_email, \
    send_appointment_reschedule_email

previous_statuses = {}


@receiver(pre_save, sender=Appointment)
def track_status_change(sender, instance, **kwargs):
    # Check if the instance is not created for the first time
    if instance.pk:
        prev = Appointment.objects.get(pk=instance.pk)
        previous_statuses[instance.pk] = prev


@receiver(post_save, sender=Appointment)
def cancel_email(sender, instance, created, **kwargs):
    if not created:
        if instance.appointment_status != previous_statuses.get(
                instance.pk).appointment_status and \
                instance.appointment_status == 'cancelled':
            send_appointment_cancelled_email({"appointment": instance.__dict__})
        if instance.scheduled_from != previous_statuses.get(
                instance.pk).scheduled_from or \
                instance.scheduled_to != previous_statuses.get(
            instance.pk).scheduled_to:
            send_appointment_reschedule_email(
                {"appointment": instance.__dict__})
