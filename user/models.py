# Create your models here.
import logging
from datetime import timedelta, datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django_rest_passwordreset.signals import reset_password_token_created

from base.helpers.email import EmailUtils
from fuelapp.constants import WEEKDAYS
from fuelapp.validators import RestrictedImageField, validate_images

logging.basicConfig(filename='fuelapp.log', level=logging.INFO)
logger = logging.getLogger('fuelapp')

# Create your models here.
GENDER = (('', 'Select'),
          ('male', 'Male'),
          ('female', 'Female'),
          ('transgender', 'Transgender'))

BLOOD_GROUP = (('', 'Select'),
               ('A+', 'A+'), ('A-', 'A-'),
               ('B+', 'B+'), ('B-', 'B-'),
               ('AB+', 'AB+'), ('AB-', 'AB-'),
               ('O+', 'O+'), ('O-', 'O-'))


class User(AbstractUser):
    # phone_regex = RegexValidator(regex=r'^[2-9]\d{9}$',
    #                              message="Phone number must be entered in "
    #                                      "the format: '999999999'.")
    phone_regex = RegexValidator(
        # regex=r'^\+?\d{10,18}$',
        regex=r'^[\+\d{10,18}]?(?:[\d\-.\s()]{10,20})$',
        # Allow '+' at the beginning and 9 to 14 digits
        message="Phone number must be entered in the format: '9999999999'."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=20,
                                    blank=True)
    secondary_phone_number = models.CharField(
        validators=[phone_regex],
        max_length=20,
        blank=True,
        null=True
    )
    email = models.EmailField('Email address', unique=False)
    username = models.CharField(max_length=50, blank=True, null=True,
                                unique=True)
    # photo = models.ImageField(null=True, blank=True)
    photo = RestrictedImageField(upload_to='uploads/user/',
                                 validators=[validate_images],
                                 max_upload_size=3145728,
                                 blank=True,
                                 null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    doctor_calender_color = models.CharField(max_length=10, null=True,
                                             blank=True)
    gender = models.CharField(choices=GENDER, blank=True, null=True,
                              default='')
    blood_group = models.CharField(choices=BLOOD_GROUP, blank=True,
                                   null=True, default='')
    email_verified = models.BooleanField('Email Verified', default=0)
    email_code = models.TextField(
        'Email Verify Code', default=None, blank=True, null=True,
        max_length=255)
    signature = RestrictedImageField(upload_to='uploads/doctor/signature/',
                                     validators=[validate_images],
                                     max_upload_size=3145728,
                                     blank=True,
                                     null=True)
    practo_id = models.CharField(max_length=200, blank=True,
                                 null=True, default='')
    atlas_id = models.CharField(max_length=100, blank=True,
                                null=True, default='')
    family = models.ForeignKey('self', on_delete=models.SET_NULL,
                               blank=True, null=True, default=None,
                               related_name="user_family")
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL,
                                    blank=True, null=True, default=None,
                                    related_name="user_referred_by")
    referred_by_source = models.CharField(max_length=100, blank=True,
                                          null=True, default='')
    national_id = models.CharField(max_length=30, blank=True,
                                   null=True, default='')
    patient_notes = models.TextField(blank=True,
                                     null=True, default='')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # def save(self, *args, **kwargs):
    #     if not self.atlas_id and not self.id:
    #         super().save(*args, **kwargs)
    #         self.atlas_id = f'{settings.PREFIX_ATLAS_ID}{str(self.id)}'
    #         super().save(*args, **kwargs)

    def __str__(self):
        return "{} {} ({})".format(self.first_name, self.last_name,
                                   self.atlas_id)

    class Meta:
        permissions = (
            ("manage_settings", "Manage Settings"),
            ("manage_reports", "Manage Reports"),
            ("manage_patients", "Manage Patients"),
        )


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args,
                                 **kwargs):
    # reverse('password_reset:reset-password-request')
    reset_url = f"{settings.FRONTEND_URL}reset-password"
    reset_link = "{}?token={}".format(
        reset_url,
        reset_password_token.key)
    try:
        subject = "Password Reset for {title}".format(
            title=settings.SITE_TITLE)

        data = {
            'user': model_to_dict(reset_password_token.user),
            'reset_link': reset_link
        }

        EmailUtils(reset_password_token.user.email,
                   subject,
                   'reset-password',
                   data).send()

    except Exception as ex:
        logger.info(f"Error - {ex}")
        return


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    address_line_1 = models.TextField(null=True, blank=True)
    address_line_2 = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=30, null=True)
    country = models.CharField(max_length=30)
    pin_code = models.IntegerField(null=True, blank=True)
    phone_no_1 = models.CharField(max_length=30, null=True, blank=True)
    phone_no_2 = models.CharField(max_length=30, null=True, blank=True)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='address_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='address_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}".format(self.type)


class DoctorTiming(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_day = models.CharField(choices=WEEKDAYS, null=True)
    start_at = models.TimeField(null=True, blank=True)
    break_1_start = models.TimeField(null=True, blank=True)
    break_1_end = models.TimeField(null=True, blank=True)
    break_2_start = models.TimeField(null=True, blank=True)
    break_2_end = models.TimeField(null=True, blank=True)
    end_at = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(null=True, blank=True)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='DoctorTiming_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='DoctorTiming_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.week_day


class Leaves(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)
    scheduled_from = models.DateTimeField(null=True, blank=True)
    scheduled_to = models.DateTimeField(null=True, blank=True)
    leave_note = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='DoctorLeave_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='DoctorLeave_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    clinic = models.ForeignKey('clinic.Clinic', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.scheduled_from} - {self.scheduled_to}"

class Otp(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{} {} ({}) - {}".format(self.user.first_name, self.user.last_name, self.user.atlas_id, self.otp)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.expires_at:
            self.expires_at = self.created_at + timedelta(minutes=10)  # OTP expires in 10 minutes
        super().save(*args, **kwargs)