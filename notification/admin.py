from django.contrib import admin

# Register your models here.
from .models import NotificationLog, Reminder, LetterRequest


@admin.register(NotificationLog)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'message')
    search_fields = ('type', 'mode', 'message')
    list_filter = ('type', 'mode')
    autocomplete_fields = ('created_by', 'updated_by', 'user')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'clinic')
    search_fields = ('title', 'clinic')
    list_filter = ('scheduled_from', 'scheduled_to', 'clinic')
    #autocomplete_fields = ('created_by', 'updated_by', 'user')


@admin.register(LetterRequest)
class LetterRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'date_and_time')
    search_fields = ('subject', 'type')
    list_filter = ('invoice', 'date_and_time', 'type')
    autocomplete_fields = ('created_by', 'updated_by', 'invoice')
