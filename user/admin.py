from django.contrib import admin

from .models import User, Address, DoctorTiming, Leaves, Otp


# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'atlas_id', 'first_name', 'last_name', 'email',
                    'get_groups', 'username', 'is_active', 'practo_id')
    search_fields = ('id', 'email', 'first_name', 'phone_number', 'secondary_phone_number', 'username',
                     'atlas_id', 'last_name', 'practo_id')
    list_filter = ('groups', 'is_active', 'gender', 'blood_group', 'date_of_birth')
    autocomplete_fields = ('groups', 'referred_by')

    def get_groups(self, obj):
        return ', '.join([group.name for group in obj.groups.all()])

    get_groups.short_description = 'Groups'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'city', 'state')
    search_fields = ('type', 'city', 'state')
    list_filter = ('type',)
    autocomplete_fields = ('created_by', 'updated_by')


@admin.register(DoctorTiming)
class DoctorTimingAdmin(admin.ModelAdmin):
    list_display = ('id', 'week_day', 'is_available')
    search_fields = ('week_day', 'start_at', 'end_at')
    list_filter = ('week_day', 'is_available')
    autocomplete_fields = ('created_by', 'updated_by', 'user')


@admin.register(Leaves)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('id', 'clinic', 'scheduled_from', 'scheduled_to', 'leave_note')
    search_fields = ('leave_note', 'user', 'clinic')
    list_filter = ('scheduled_from', 'scheduled_to', 'clinic')
    autocomplete_fields = ('created_by', 'updated_by',)

admin.site.register(Otp)
class OtpAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'created_at', 'expires_at', 'is_used', 'attempts', 'sent_at')
    search_fields = ('user__email', 'otp')
    list_filter = ('is_used', 'created_at', 'expires_at')
    readonly_fields = ('created_at', 'expires_at', 'sent_at')    