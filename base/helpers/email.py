import json
import logging

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger('fuelapp')


class EmailUtils:
    def __init__(self, to_email, subject, template_name, context, clinic=None, method=None):
        self.to_email = to_email
        self.subject = subject
        self.template_name = template_name
        self.context = context
        self.clinic = clinic
        # Use API if True, else use
        self.use_api = method if method else settings.EMAIL_METHOD
        # Django email
        self.EMAIL_API_URL = settings.EMAIL_API_URL

        self.validate_email()

    def validate_email(self):
        # You can add more complex email validation logic here.
        if not "@" in self.to_email:
            raise ValidationError("Invalid email address")

    def render_template(self):
        # Render the email content using the Django template and context.
        file = f"{self.template_name}.html" if self.template_name.find(
            ".html") == -1 \
            else self.template_name

        return render_to_string(file, self.context)

    def send(self):
        try:
            if not settings.EMAIL_ENABLED:
                raise Exception("Unable to send email, Email is not enabled on "
                                "this application")
            if self.clinic and not self.clinic.enable_email:
                logger.info(f"Email not enabled for clinic: {self.clinic.name}")
                return False
            email_body = self.render_template()

            if self.use_api:
                # Create a payload with the email details.
                payload = json.dumps({
                    "to_email": self.to_email,
                    "subject": self.subject,
                    "body": email_body,
                })

                headers = {
                    'Content-Type': 'application/json',
                }

                # Send the email using the cURL-based API.
                response = requests.post(self.EMAIL_API_URL, headers=headers,
                                         data=payload)
                if response.status_code != 200:
                    raise Exception(response.text)
                return response.text
            else:
                # Send the email using Django's email functionality.
                is_success = send_mail(
                    subject=self.subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.to_email],
                    fail_silently=False,
                    html_message=email_body
                )
                return is_success
        except Exception as ex:
            logger.info(f"error on send mail utils - {ex}")
        return False
