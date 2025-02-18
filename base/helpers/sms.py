import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string


# SMSUtils().send(9551167804,{'first_name': 'abdul','clinic':'a'},'sms/create_appointment.txt')
class SMSUtils:
    URL = ""
    templates = {
        'create_appointment': 'sms/create_appointment.txt',
        'cancelled_appointment': 'sms/cancelled_appointment.txt',
        'review_appointment': 'sms/review_appointment.txt',
        'reset_password': 'sms/reset_password.txt',
        'appointment_booked_by_staff': 'sms/appointment_booked_by_staff.txt',
        'appointment_booked_by_patient': 'sms/appointment_booked_by_patient.txt',
        'appointment_instruction': 'sms/appointment_instruction.txt',
        'confirm_payment': 'sms/confirm_payment.txt',
        'confirmation_code': 'sms/confirmation_code.txt',
        'location_link': 'sms/location_link.txt',
        'appointment_payment_link': 'sms/appointment_payment_link.txt'
    }

    def __init__(self, template, clinic=None):
        if not settings.SMS_ENABLED:
            logging.info("SMS is not enabled on this application")
        self.clinic = clinic    
        self.BASE_URL = settings.SMS_API_URL
        self.SENDER = settings.SMS_API_SENDER
        self.USER = settings.SMS_API_USER
        self.PASS = settings.SMS_API_PASS
        self.PRIORITY = 'ndnd'
        self.STYPE = 'normal'
        self.TEMPLATE = self.templates.get(template, False)

    def send(self, phone, data):
        if not settings.SMS_ENABLED:
            logging.info("SMS is not enabled on this application")
            return False
        if self.clinic and not self.clinic.enable_sms:
            logging.info(f"SMS not enabled for clinic: {self.clinic.name}")
            return False
        if not self.TEMPLATE:
            logging.info(f"Template {self.TEMPLATE} not found")
            return False
            # raise Exception(f"Template {self.TEMPLATE} not found")
        if not isinstance(data, dict):
            logging.info("Data must be a dictionary")
            return False
            # raise Exception("Data must be a dictionary")
        if not phone:
            logging.info("Phone number is required")
            return False
            # raise Exception("Phone number is required")
        text = render_to_string(self.TEMPLATE, data)
        params = {
            'user': self.USER,
            'pass': self.PASS,
            'sender': self.SENDER,
            'phone': phone,
            'text': text,
            'priority': self.PRIORITY,
            'stype': self.STYPE
        }
        build_params = "&".join(
            [f"{key}={value}" for key, value in params.items()])
        url = f"{self.BASE_URL}?{build_params}"
        # url = "http://bhashsms.com/api/sendmsg.php?user=hello2minstudio&
        # pass=123456&sender=ATLSIN&phone=9344650757&
        # text=Hello Tamil Selvi How are you&priority=ndnd&stype=normal"

        response = requests.request("GET", url)
        logging.info(response.text)
        if response.status_code != 200:
            # raise Exception(response.text)
            logging.info(response.text)
        logging.info(f"sent SMS to {phone} - using tempalte {self.TEMPLATE} "
                     f" response: {response.text}")
        return response.text