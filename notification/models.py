from django.db import models

from payment.models import Invoice
from user.models import User

# Create your models here.

MODE = (
    ('sms', "SMS"),
    ('whatsapp', "Whatsapp"),
    ('email', "Email")
)

TYPE = (
    ('general', 'General'),
    ('confirm_appointment', 'Confirm Appointment'),
    ('cancel_appointment', 'Cancel Appointment'),
    ('payment', 'Payment'),
    ('reminder', 'Reminder')
)


class NotificationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(null=True, blank=True)
    type = models.CharField(choices=TYPE, max_length=30)
    mode = models.CharField(choices=MODE, max_length=20, default='email')
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='notification_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='notification_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} {}".format(self.type, self.mode)


# https://app.zeplin.io/project/61ff6dc4c092459b1dc5665e/screen/645b7f1f82e16a0df49351fd
class NotificationConfig(models.Model):
    mode = models.Choices


class Reminder(models.Model):
    clinic = models.ForeignKey('clinic.Clinic', on_delete=models.CASCADE, null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    scheduled_from = models.DateTimeField(null=True, blank=True)
    scheduled_to = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


LETTER_TYPE = (
    ('billing', "Billing"),
    ('treatment_plan', "Treatment Plan"),
    ('medical_leave', "Medical Leave")
)


# https://app.zeplin.io/project/61ff6dc4c092459b1dc5665e/screen/645b7f424aada040a2a78ae1
# class Signatures(models.Model):


class LetterRequest(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    date_and_time = models.DateTimeField(null=True, blank=True)
    subject = models.TextField(null=True, blank=True)
    # invoice_items = models.TextField(null=True, blank=True)
    # payment_details = models.FloatField(null=True, blank=True)
    type = models.CharField(choices=LETTER_TYPE, max_length=20)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='letterrequest_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='letterrequest_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}".format(self.type)
