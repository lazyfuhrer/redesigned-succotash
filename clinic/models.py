from django.db import models
from django.db.models import ManyToManyField

from fuelapp.constants import WEEKDAYS
from user.models import User


# Create your models here.


class Clinic(models.Model):
    SLOT_DURATION = (
        ('15', '15 Mins'),
        ('30', '30 Mins'),
        ('45', '45 Mins'),
        ('60', '1 Hour'),
    )
    logo = models.ImageField(null=True, blank=True)
    name = models.CharField(max_length=30)
    tagline = models.CharField(max_length=150)
    address_line_1 = models.TextField(null=True, blank=True)
    address_line_2 = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=15)
    state = models.CharField(max_length=30)
    country = models.CharField(max_length=30)
    pincode = models.IntegerField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone_no_1 = models.BigIntegerField(null=True, blank=True)
    phone_no_2 = models.BigIntegerField(null=True, blank=True)
    website = models.CharField(max_length=100, null=True, blank=True)
    map_link = models.CharField(max_length=250, null=True, blank=True)
    review_link = models.TextField(null=True, blank=True)
    slot_duration = models.CharField(choices=SLOT_DURATION, default='15',
                                     max_length=10)
    status = models.BooleanField(default=1)
    enable_email = models.BooleanField(default=True)
    enable_sms = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='clinic_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='clinic_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ClinicPeople(models.Model):
    # clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    clinic = ManyToManyField(Clinic)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='clinicpeople_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='clinicpeople_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} {} {}".format(self.user, self.user.groups, self.clinic)


class ClinicTiming(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
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
        related_name='clinictiming_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='clinictiming_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} {}".format(self.week_day, self.clinic)

class ClinicDay(models.Model):
    name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name