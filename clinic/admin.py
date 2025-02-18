from django.contrib import admin

from .models import Clinic, ClinicPeople, ClinicTiming, ClinicDay


# Register your models here.
@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'website')
    autocomplete_fields = ('created_by', 'updated_by')
    search_fields = ('name', 'city', 'state')
    list_filter = ('slot_duration',)


@admin.register(ClinicPeople)
class ClinicPeopleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user')
    autocomplete_fields = ('user', 'created_by', 'updated_by')
    search_fields = ('clinic',)
    list_filter = ('clinic',)


@admin.register(ClinicTiming)
class ClinicTimingAdmin(admin.ModelAdmin):
    list_display = ('id', 'week_day', 'start_at', 'clinic', 'is_available',
                    'end_at')
    autocomplete_fields = ('created_by', 'updated_by')
    search_fields = ('week_day', 'start_at', 'end_at')
    list_filter = ('clinic', 'week_day', 'is_available')

@admin.register(ClinicDay)
class ClinicDayAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)