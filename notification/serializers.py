from rest_framework import serializers

from .models import NotificationLog, NotificationConfig, Reminder, LetterRequest


class NotificationLogSerializer(serializers.Serializer):
    class Meta:
        models = NotificationLog
        fields = (
            'user',
            'message',
            'type',
            'mode',
        )


class NotificationConfigSerializer(serializers.Serializer):
    class Meta:
        models = NotificationConfig
        fields = (
            'mode',
        )


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = [
            'id',
            'title',
            'clinic',
            'scheduled_from',
            'scheduled_to',
            ]
        
    def get_title(self, obj):
        return f"{obj.title}"
    
class LetterRequestSerializer(serializers.Serializer):
    class Meta:
        models = LetterRequest
        fields = (
            'invoice',
            'date_and_time',
            'subject',
            'type',
        )
