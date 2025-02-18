from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, username=None, password=None,
                     **kwargs):
        try:
            if email:
                user = User.objects.get(
                    Q(email__iexact=email) | Q(username__iexact=email))
            elif username:
                user = User.objects.get(
                    Q(email__iexact=username) | Q(username__iexact=username))
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
