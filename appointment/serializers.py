from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework import serializers

from user.models import User
from user.serializers import UserSerializer
from clinic.serializers import ClinicDaySerializer
from .models import Appointment, Procedure, Tax, Category, PatientDirectory, \
    Files, Exercise, PatientDirectoryExercises, NoteCategory, DoctorCategory, AppointmentState
from payment.utils import get_invoice_items


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField(read_only=True)
    doctor_color = serializers.StringRelatedField(source='doctor.doctor_calender_color', read_only=True)
    clinic_name = serializers.StringRelatedField(source='clinic.name')
    patient_name = serializers.SerializerMethodField(read_only=True)
    patient_email = serializers.StringRelatedField(source='patient.email', read_only=True)
    patient_phone_number = serializers.StringRelatedField(source='patient.phone_number', read_only=True)
    patient_first_name = serializers.SerializerMethodField(read_only=True)
    patient_last_name = serializers.SerializerMethodField(read_only=True)
    category_name = serializers.SerializerMethodField(read_only=True)
    procedure_name = serializers.SerializerMethodField(read_only=True)
    waiting_duration = serializers.SerializerMethodField(read_only=True)
    engaged_duration = serializers.SerializerMethodField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    items = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id',
            'is_new',
            'doctor',
            'doctor_name',
            'doctor_color',
            'clinic',
            'clinic_name',
            'patient',
            'patient_name',
            'patient_first_name',
            'patient_last_name',
            'patient_email',
            'patient_phone_number',
            'category',
            'category_name',
            'scheduled_from',
            'scheduled_to',
            'notes',
            'procedure',
            'procedure_name',
            'waiting_duration',
            'engaged_duration',
            'payment_status',
            'checked_in',
            'engaged_at',
            'checked_out',
            'appointment_status',
            'cancel_notes',
            'created_by',
            'updated_by',
            'items'
        )

    def get_items(self, obj):
        return get_invoice_items(obj.id)

    def get_doctor_name(self, obj):
        if obj.doctor:
            return f"{obj.doctor.first_name} {obj.doctor.last_name}"
        return ""

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_patient_first_name(self, obj):
        if obj.patient:
            return obj.patient.first_name
        return ""

    def get_patient_last_name(self, obj):
        if obj.patient:
            return obj.patient.last_name
        return ""

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        return ""

    def get_procedure_name(self, obj):
        if obj.procedure:
            return obj.procedure.name
        return ""

    def get_waiting_duration(self, obj):
        if obj.checked_in and obj.engaged_at:
            return obj.engaged_at - obj.checked_in
        return 0

    def get_engaged_duration(self, obj):
        if obj.checked_out and obj.engaged_at:
            return obj.checked_out - obj.engaged_at
        return 0

    def validate(self, data):
        req = self.context.get('request')
        method = req._request.method
        s_from = data.get('scheduled_from')
        s_to = data.get('scheduled_to')
        # doctor = data.get('doctor')
        # clinic = data.get('clinic')
        if method == "POST":
            for field in ['category', 'scheduled_from',
                          'scheduled_to']:
                if not data.get(field):
                    raise serializers.ValidationError({
                        field: f"{field} not valid"
                    })

        if method == "POST" and not s_from:
            raise serializers.ValidationError({
                'scheduled_from': "Start time not valid"
            })

        if method == "POST" and not s_to:
            raise serializers.ValidationError({
                'scheduled_to': "End time not valid"
            })
        if s_from and s_to:
            # if req and req._request.method == "POST":
            # validate no appointment exist for this doctor with time between
            # doctor_busy = Appointment.objects.filter(doctor=doctor,
            #                                          scheduled_from__lt=s_to,
            #                                          scheduled_to__gt=s_from)
            # if req and req.method == "PATCH":
            #     pid = req.parser_context['kwargs'].get('pk')
            #     doctor_busy = doctor_busy.exclude(id=pid)

            # if doctor_busy.exists():
            #     raise serializers.ValidationError({
            #         'general': "Appointment time overlaps with an existing "
            #                    f"appointment of Dr. {doctor}. Please choose "
            #                    "a new time."
            #     })

            # validate start and end time should not same and not less than
            if not s_from:
                raise serializers.ValidationError({
                    'scheduled_from': "Start time not valid"
                })

            if not s_to:
                raise serializers.ValidationError({
                    'scheduled_to': "End time not valid"
                })

            if s_to <= s_from:
                raise serializers.ValidationError({
                    'scheduled_to': "End time should be greater then start "
                                    "time."
                })

            # wday = s_from.strftime(
            #     '%A')  # Get the week day of the s_from

            # if clinic:
            #     try:
            #         clinic_timing = ClinicTiming.objects.get(clinic=clinic,
            #                                                  week_day__iexact=wday)
            #     except ClinicTiming.DoesNotExist:
            #         raise serializers.ValidationError(
            #             f"Invalid clinic {clinic} timing on {wday}.")
            #
            #     if not clinic_timing.start_at <= s_from.time() <= s_to.time() \
            #            <= clinic_timing.end_at:
            #         raise serializers.ValidationError(
            #             f"Appointment start time should be within {clinic} "
            #             f"clinic operating hours. {clinic_timing.start_at} - "
            #             f"{clinic_timing.end_at}")

            # if clinic_timing.break_1_start and clinic_timing.break_1_end:
            #     if clinic_timing.break_1_start < s_from.time() < \
            #             clinic_timing.break_1_end or \
            #             clinic_timing.break_1_start < s_to.time() < \
            #             clinic_timing.break_1_end:
            #         raise serializers.ValidationError(
            #             "Appointment should not fall within break 1 "
            #             f"timings of {clinic}.")

            # if clinic_timing.break_2_start and clinic_timing.break_2_end:
            #     if clinic_timing.break_2_start < s_from.time() < \
            #             clinic_timing.break_2_end or \
            #             clinic_timing.break_2_start < s_to.time() < \
            #             clinic_timing.break_2_end:
            #         raise serializers.ValidationError(
            #             "Appointment should not fall within break 2 "
            #             f"timings of {clinic}.")

        return data


class ProcedureSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    tax_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Procedure
        fields = (
            'id',
            'clinic',
            'name',
            'description',
            'cost',
            'tax',
            'tax_info',
            'created_by',
            'updated_by'
        )

    def get_tax_info(self, obj):
        taxes = obj.tax.all()
        return TaxSerializer(instance=taxes, many=True).data


class TaxSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Tax
        fields = (
            'id',
            'name',
            'percentage',
            'created_by',
            'updated_by'
        )


class CategorySerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Category
        fields = (
            'id',
            'name',
            'clinic',
            'created_by',
            'updated_by'
        )


class NoteCategorySerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = NoteCategory
        fields = (
            'id',
            'name',
            'created_by',
            'updated_by'
        )


class FilesSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Files
        fields = (
            'id',
            'patient_directory',
            'file_url',
            'file_name',
            'created_by',
            'updated_by'
        )

    def validate(self, data):
        request = self.context.get('request')
        files = request.FILES.getlist('file')
        for file in files:
            self.validate_file_size(file)
            self.validate_file_type(file)
        return data

    def validate_file_size(self, file):
        if file.size > settings.MAX_FILE_SIZE:
            raise ValidationError(
                f"File {file.name} exceeds the maximum size of {settings.MAX_FILE_SIZE / (1024 * 1024)} MB.")

    def validate_file_type(self, file):
        if file.content_type not in settings.ALLOWED_FILE_TYPES:
            raise ValidationError(
                f"File {file.name} is not an allowed type. Allowed types are: {', '.join(settings.ALLOWED_FILE_TYPES)}.")


class PatientDirectorySerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    category_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PatientDirectory
        fields = (
            'id',
            'appointment',
            'category',
            'category_name',
            'notes',
            'clinical_note_type',
            'created_by',
            'updated_by',
            'files'
        )

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name

    def get_files(self, obj):
        files = Files.objects.filter(patient_directory=obj.id)
        return FilesSerializer(instance=files, many=True).data


class ExerciseSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Exercise
        fields = (
            'id',
            'title',
            'video_clips',
            'video_link',
            'summary',
            'created_by',
            'updated_by'
        )


class PatientDirectoryExercisesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDirectoryExercises
        fields = (
            'id',
            'patient_directory',
            'exercise',
            'created_by',
            'updated_by'
        )


class CreateAppointmentSerializer(serializers.ModelSerializer):
    patient = UserSerializer()

    class Meta:
        model = Appointment
        fields = ['doctor', 'clinic', 'category', 'procedure',
                  'scheduled_from', 'scheduled_to', 'patient']

    def create(self, validated_data):
        patient_data = validated_data.pop('patient')
        email = patient_data.get('email')
        # print(email)
        patient_instance, is_created = User.objects.get_or_create(email=email)
        # patient_instance, is_created = User.objects.get_or_create(
        #     **patient_data)
        appointment_instance = Appointment.objects.create(
            patient=patient_instance,
            is_new=is_created,
            **validated_data)
        return appointment_instance

class DoctorCategorySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_clinic_name = serializers.CharField(source='category.clinic', read_only=True)
    available_days = ClinicDaySerializer(many=True, read_only=True)

    class Meta:
        model = DoctorCategory
        fields = ['id', 'doctor', 'category', 'doctor_name', 'category_name', 'category_clinic_name', 'available_days', 'created_at', 'updated_at']


class AvailableDoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"    
    
class AppointmentStateSerializer(serializers.ModelSerializer):
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    appointment_details = AppointmentSerializer(source='appointment', read_only=True)

    class Meta:
        model = AppointmentState
        fields = (
            'id',
            'appointment',
            'payment_status',
            'payment_status_display',
            'appointment_details',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('payment_status', 'created_at', 'updated_at')    