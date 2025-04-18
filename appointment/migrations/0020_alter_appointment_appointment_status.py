# Generated by Django 4.2.13 on 2024-12-28 18:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointment', '0019_appointmentstate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='appointment_status',
            field=models.CharField(choices=[('booked', 'Booked'), ('checked_in', 'Checked In'), ('engaged', 'Engaged'), ('checked_out', 'Checked Out'), ('cancelled', 'Cancelled'), ('not_visited', 'Not Visited'), ('waiting', 'Waiting')], default='booked', max_length=20),
        ),
    ]
