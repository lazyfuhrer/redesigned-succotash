import hashlib
import logging
import random
import string
import urllib

from django.conf import settings
from django.forms.models import model_to_dict

from base.helpers.email import EmailUtils

# logging.basicConfig(filename='fuelapp.log', level=logging.INFO)
logger = logging.getLogger('fuelapp')

def gen_rand_code():
    N = 7
    randstring = str(''.join(random.choices(string.ascii_uppercase +
                                            string.digits, k=N)))
    code = randstring.encode()
    md5code = hashlib.md5(code).hexdigest()
    return md5code


def send_verify_code(user):
    query = {'code': user.email_code, 'email': user.email}
    qstr = urllib.parse.urlencode(query)
    verify_link = "{base}verify?{query}".format(
        base=settings.FRONTEND_URL,
        query=qstr)
    data = {'user': model_to_dict(user), 'verify_link': verify_link}
    subject = "Welcome to {title} | Verify your email".format(
        title=settings.SITE_TITLE)
    EmailUtils(user.email,
               subject,
               'welcome',
               data).send()

def generate_otp():
    return ''.join(random.choices('123456789', k=6))

def mask_name(name):
    if len(name) <= 4:
        return name
    return name[:2] + '*' * (len(name) - 4) + name[-2:]