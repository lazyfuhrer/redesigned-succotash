from time import sleep

from celery import shared_task
from django.utils import timezone

from appointment.models import Appointment
from appointment.serializers import AppointmentSerializer
from base.utils import send_appointment_reminder_email, \
    appointment_instructions_notification, appointment_feedback_notification


@shared_task
def health_check(arg):
    # Your task logic goes here
    print(arg)
    sleep(5)
    print('Health check is done!')


@shared_task
def daily_task():
    # list all daily tasks are here
    # Tomorrow appointment notificaitons
    reminder_appointments.delay()
    instruction_appointments.delay()
    print('daily task')


@shared_task
def reminder_appointments():
    tomorrow = timezone.now().date() + timezone.timedelta(days=1)
    appointments = Appointment.objects.filter(
        scheduled_from=tomorrow
    )
    serializer_data = AppointmentSerializer(appointments, many=True).data
    for appointment in serializer_data:
        send_appointment_reminder_email({appointment: appointment})
    # for appointment in serializer_data:
    #     send_appointment_reminder_email({appointment: appointment})
    print('reminder_appointments action completed')


@shared_task
def instruction_appointments():
    tomorrow = timezone.now().date() + timezone.timedelta(days=1)
    appointments = Appointment.objects.filter(
        scheduled_from=tomorrow
    )
    serializer_data = AppointmentSerializer(appointments, many=True).data
    for appointment in serializer_data:
        appointment_instructions_notification({appointment: appointment})
    print('instruction_appointments action completed')


# collect feedback
@shared_task
def review_feedback_appointments():
    yeterday = timezone.now().date() - timezone.timedelta(days=1)
    appointments = Appointment.objects.filter(
        scheduled_from=yeterday, appointment_status='completed'
    )
    serializer_data = AppointmentSerializer(appointments, many=True).data
    for appointment in serializer_data:
        appointment_feedback_notification({appointment: appointment})
    print('review_feedback_appointments action completed')
