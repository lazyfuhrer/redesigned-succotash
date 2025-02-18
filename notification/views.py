from rest_framework import generics

from .models import NotificationLog, NotificationConfig, Reminder, LetterRequest
from .serializers import NotificationLogSerializer, \
    NotificationConfigSerializer, \
    ReminderSerializer, LetterRequestSerializer


# Create your views here.


# Create your views here.


class NotificationLogList(generics.ListCreateAPIView):
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer

    def get_queryset(self):
        queryset = NotificationLog.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class NotificationLogView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer


class NotificationConfigList(generics.ListCreateAPIView):
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer

    def get_queryset(self):
        queryset = NotificationConfig.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class NotificationConfigView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer


class ReminderList(generics.ListCreateAPIView):
    queryset = Reminder.objects.all()
    serializer_class = ReminderSerializer

    def get_queryset(self):
        queryset = Reminder.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class ReminderListView(generics.ListAPIView):
    serializer_class = ReminderSerializer

    def get_queryset(self):
        clinic = self.request.query_params.get('clinic')
        scheduled_from = self.request.query_params.get('scheduled_from')
        scheduled_to = self.request.query_params.get('scheduled_to')

        # Filter queryset by the selected date range
        queryset = Reminder.objects.filter(
            scheduled_from__gte=scheduled_from,
            scheduled_from__lt=scheduled_to
        ).order_by('scheduled_from')

        if clinic:
            queryset = queryset.filter(clinic=clinic)
        if scheduled_from:
            queryset = queryset.filter(scheduled_from=scheduled_from)
        if scheduled_to:
            queryset = queryset.filter(scheduled_to=scheduled_to)

        return queryset
    
class ReminderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Reminder.objects.all()
    serializer_class = ReminderSerializer

class LetterRequestList(generics.ListCreateAPIView):
    queryset = LetterRequest.objects.all()
    serializer_class = LetterRequestSerializer

    def get_queryset(self):
        queryset = LetterRequest.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset

class LetterRequestView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LetterRequest.objects.all()
    serializer_class = LetterRequestSerializer
