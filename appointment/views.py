# Create your views here.
import json, uuid, logging, traceback

from datetime import timedelta, datetime
from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.db.models.functions import Lower
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from rest_framework import generics, status, filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from base.utils import send_appointment_followup_email, \
    appointment_booked_notification
from user.serializers import UserSerializer
from .models import Appointment, Procedure, Tax, Category, PatientDirectory, \
    Files, Exercise, PatientDirectoryExercises, NoteCategory, Clinic, DoctorCategory, \
    AppointmentState
from .serializers import AppointmentSerializer, ProcedureSerializer, \
    TaxSerializer, NoteCategorySerializer, CategorySerializer, PatientDirectorySerializer, \
    FilesSerializer, ExerciseSerializer, AvailableDoctorSerializer, \
    PatientDirectoryExercisesSerializer
from payment.views import process_payment, process_razorpay_payment
from clinic.models import ClinicTiming

logger = logging.getLogger('fuelapp')

# Create your views here.
User = get_user_model()

class AppointmentList(generics.ListCreateAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)
        # place send email logic here on schedule followup
        if self.request.query_params.get('schedule') == 'true':
            send_appointment_followup_email({"appointment": serializer.data})

    def get_queryset(self):
        # Exclude appointments with payment_status 'pending'
        queryset = Appointment.objects.exclude(
            appointmentstate__payment_status='pending'
        )

        # Include appointments with payment_status 'pending' and appointment_status 'waiting'
        queryset = queryset | Appointment.objects.filter(
            Q(appointmentstate__payment_status='pending') & Q(appointment_status='waiting')
        )
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class AppointmentAll(generics.ListAPIView):
    permission_classes = []
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    pagination_class = None

    def get_queryset(self):
        # Exclude appointments with payment_status 'pending'
        queryset = Appointment.objects.exclude(
            appointmentstate__payment_status='pending'
        )

        # Include appointments with payment_status 'pending' and appointment_status 'waiting'
        queryset = queryset | Appointment.objects.filter(
            Q(appointmentstate__payment_status='pending') & Q(appointment_status='waiting')
        )

        queryset = queryset.order_by('-scheduled_from')
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class AppointmentView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        cancel_notes = self.request.data.get('cancel_notes', None)
        if cancel_notes:
            serializer.save(updated_by=self.request.user, cancel_notes=cancel_notes)
        else:
            serializer.save(updated_by=self.request.user)
            

class ProcedureList(generics.ListCreateAPIView):
    queryset = Procedure.objects.all()
    model = Procedure
    serializer_class = ProcedureSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Procedure.objects.all().order_by('name')
        params = self.request.query_params
        search_term = params.get('search', '')

        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search', 'page_size']:
                    queryset = queryset.filter(**{param: params[param]})

        if search_term:
            # Annotate the queryset to prioritize names starting with the search term
            queryset = queryset.annotate(
                starts_with=Case(
                    When(name__istartswith=search_term, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-starts_with', Lower('name'))

        return queryset

class ProcedureView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Procedure.objects.all()
    serializer_class = ProcedureSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class TaxList(generics.ListCreateAPIView):
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Tax.objects.all().order_by('-created_at')
        params = self.request.query_params
        if len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class TaxView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tax.objects.all()
    serializer_class = TaxSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Category.objects.annotate(
            custom_order=Case(
                When(name__iexact='chiropractic', then=Value(1)),
                When(name__iexact='physiotherapy', then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('custom_order', 'name')
        params = self.request.query_params
        if len(params) > 0:
            for param in params:
                if param not in ['page', 'search', 'page_size']:
                    queryset = queryset.filter(**{param: params[param]})                 
        return queryset


class CategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class NoteCategoryList(generics.ListCreateAPIView):
    queryset = NoteCategory.objects.all()
    serializer_class = NoteCategorySerializer
    search_fields = ['name']

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = NoteCategory.objects.all().order_by('-created_at')
        params = self.request.query_params
        if len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class NoteCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NoteCategory.objects.all()
    serializer_class = NoteCategorySerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class PatientDirectoryList(generics.ListCreateAPIView):
    queryset = PatientDirectory.objects.all()
    serializer_class = PatientDirectorySerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = PatientDirectory.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class PatientDirectoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatientDirectory.objects.all()
    serializer_class = PatientDirectorySerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class FilesList(generics.ListCreateAPIView):
    queryset = Files.objects.all()
    serializer_class = FilesSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Files.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class FilesView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Files.objects.all()
    serializer_class = FilesSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class ExerciseList(generics.ListCreateAPIView):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Exercise.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class ExerciseView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class PatientDirectoryExercisesList(generics.ListCreateAPIView):
    queryset = PatientDirectoryExercises.objects.all()
    serializer_class = PatientDirectoryExercisesSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = PatientDirectoryExercises.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class PatientDirectoryExercisesView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatientDirectoryExercises.objects.all()
    serializer_class = PatientDirectoryExercisesSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


# this view allows create or update note form frontend
class CreateNotesView(APIView):
    def post(self, request):
        data = request.data
        clinical_note_type = data.get('clinical_note_type')
        exercise = data.get('exercise')
        appointment = data.get('appointment')
        category = data.get('category')
        notes = data.get('notes')
        note_id = data.get('id', '')
        session = {'created_by': self.request.user.id, 'updated_by': self.request.user.id}
        note = {
            'appointment': appointment,
            'category': category,
            'notes': notes,
            'clinical_note_type': clinical_note_type,
        }
        note.update(session)

        if note_id:
            success_status = status.HTTP_200_OK
            instance = PatientDirectory.objects.filter(id=note_id).first()
        else:
            success_status = status.HTTP_201_CREATED
            instance = None

        serializer = PatientDirectorySerializer(data=note, instance=instance, partial=True)

        if serializer.is_valid():
            pd = serializer.save()
            note_id = pd.id  # Ensure we have the saved instance ID for file associations
            files = request.FILES.getlist('file')  # Get the list of uploaded files
            if files:
                path = f'/files/appointment_{appointment}/note_{note_id}'
                upload_location = f'{settings.UPLOADS_ROOT}{path}'
                fs = FileSystemStorage(location=upload_location)
                for file in files:
                    # Create a new instance of the FilesSerializer
                    file_data = {
                        'patient_directory': note_id,
                        'file_name': file.name,
                        'created_by': request.user.id,
                        'updated_by': request.user.id,
                    }
                    file_serializer = FilesSerializer(data=file_data, context={'request': request})
                    if file_serializer.is_valid(raise_exception=True):
                        filename = fs.save(file.name, file)
                        file_url = fs.url(filename)
                        # Update file_url in serializer data
                        file_serializer.save(file_url=path + file_url)

            if clinical_note_type == 'exercise':
                ex_data = {'patient_directory': pd, 'exercise': exercise}
                ex_data.update(session)
                pde_serializer = PatientDirectoryExercisesSerializer(data=ex_data)
                if pde_serializer.is_valid():
                    pde_serializer.save()
                else:
                    return Response(pde_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.data, status=success_status)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateAppointment(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        photo = request.FILES.get('photo')
        data = request.POST.get('data')
        data_object = json.loads(data)
        patient = data_object.pop('patient')
        email = patient.get('email')
        phone_number = patient.get('phone_number')
        first_name = patient.get('first_name')
        last_name = patient.get('last_name')
        patient_id = patient.get('id')
        try:
            if patient_id:
                user = User.objects.get(pk=patient_id)
                if user.first_name != first_name or (last_name and user.last_name != last_name):
                    raise ObjectDoesNotExist
                if user.email and user.email != email:
                    raise ObjectDoesNotExist
                if user.phone_number and user.phone_number != phone_number:
                    raise ObjectDoesNotExist
                
                # Update user details if missing
                if not user.email and email:
                    user.email = email
                if not user.phone_number and phone_number:
                    user.phone_number = phone_number
                user.save()
            else:    
                raise ObjectDoesNotExist
            data_object.update({'patient': user.id, 'is_new': False})
        except ObjectDoesNotExist:
            patient.update({'photo': photo})
            user_serializer = UserSerializer(data=patient)
            if user_serializer.is_valid():
                user_data = user_serializer.save()
                user = User.objects.get(pk=user_data.id)
                group = Group.objects.get(pk=settings.PATIENT_GROUP_ID)
                user.groups.add(group)
                user.atlas_id = f"{settings.PREFIX_ATLAS_ID}{user.id}"
                group.user_set.add(user)
                user.save()
                data_object.update({'patient': user_serializer.data['id'],
                                    'is_new': True})
            else:
                return Response(user_serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)

        # if user:
        #     data.update({'patient': user.__dict__})
        # else:
        data_object.update({'created_by': self.request.user.id,
                            'updated_by': self.request.user.id})
        serializer = AppointmentSerializer(data=data_object,
                                           context={'request': request})

        if serializer.is_valid():
            appointment = serializer.save()
            send_payment_link = data_object.get('send_payment_link', False)

            if not send_payment_link:
                appointment_booked_notification({"appointment": data_object})
            if send_payment_link:

                pending_appointment = AppointmentState.objects.create(
                    appointment=appointment,
                    payment_status='pending'
                )

                data_object.update({'appointment': appointment})

                patient_data = {
                    "user_id": data_object["patient"],
                    "phone_number": phone_number,
                    "email": email,
                    "full_name": f"{first_name} {last_name}".strip()
                }

                # try:
                #     response = process_payment(patient_data)
                #     response.raise_for_status()
                #     response_data = response.json()
                #     code = response_data.get('code')

                #     if not response_data.get('success'):
                #         pending_appointment.delete()
                #         return Response({
                #             'state': False,
                #             'code': code,
                #             'data': {
                #                 'Error': [response_data["message"]]
                #             }
                #         }, status=response.status_code)

                #     if code == 'PAYMENT_INITIATED':
                #         send_payment_notifications(
                #             user,
                #             data_object.get('clinic'),
                #             shorten_url(response_data["data"]["instrumentResponse"]["redirectInfo"]["url"])
                #         )
                    
                #         cache.set(response_data["data"]["merchantTransactionId"], data_object, 900)
                #         return Response(
                #             serializer.data, 
                #             status=status.HTTP_201_CREATED
                #         )

                # except Exception as e:
                #     pending_appointment.delete()
                #     logger.error(f"Payment processing error: {e}")
                #     logger.error(traceback.format_exc())
                #     return Response({
                #         'state': False,
                #         'data': {
                #             'Error': [str(e)]
                #         }
                #     }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                try:
                    response = process_razorpay_payment(patient_data)
                    if response and 'id' in response:
                        # change cache expiry time if needed
                        cache.set(response["id"], data_object, 2592000)
                        return Response(
                            serializer.data,
                            status=status.HTTP_201_CREATED
                        )
                    else:
                        pending_appointment.delete()
                        logger.error("Error occured")
                        return Response({
                            'state': False,
                            'data': {
                                'Error': ["Error occured"]
                            }
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    pending_appointment.delete()
                    logger.error(f"Payment processing error: {e}")
                    logger.error(traceback.format_exc())
                    return Response({
                        'state': False,
                        'data': {
                            'Error': [str(e)]
                        }
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
           
            return Response(
                serializer.data, 
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # serializer_class = CreateAppointmentSerializer
    # queryset = Appointment.objects.all()
    #
    # def perform_create(self, serializer):
    #     # Set created_by and updated_by fields
    #     serializer.save(created_by=self.request.user,
    #                     updated_by=self.request.user)

class UpComingsListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        # Get the current date and time
        now = timezone.now()
        # Use the current date
        selected_date = now.date()

        # Calculate the start and end of the selected date
        start_of_day = timezone.make_aware(
            timezone.datetime.combine(selected_date, timezone.datetime.min.time())
        )
        end_of_day = start_of_day + timedelta(days=1)

        # Filter queryset by the selected date range
        queryset = Appointment.objects.filter(
            scheduled_from__gte=start_of_day,
            scheduled_from__lt=end_of_day
        ).order_by('scheduled_from')

        # Exclude appointments with payment_status 'pending'
        queryset = queryset.exclude(
            appointmentstate__payment_status='pending'
        )

        # Include appointments with payment_status 'pending' and appointment_status 'waiting'
        queryset = queryset | Appointment.objects.filter(
            Q(appointmentstate__payment_status='pending') & Q(appointment_status='waiting'),
            scheduled_from__gte=start_of_day,
            scheduled_from__lt=end_of_day
        )

        # Get the clinic query parameter
        clinic = self.request.query_params.get('clinic')
        if clinic:
            queryset = queryset.filter(clinic=clinic)

        return queryset

class DoctorsAppointmentsListView(APIView):
    def get(self, request):
        # Get the current date and time
        now = timezone.now()
        selected_date = now.date()

        # Calculate the start and end of the selected date
        start_of_day = timezone.make_aware(
            timezone.datetime.combine(selected_date, timezone.datetime.min.time())
        )
        end_of_day = start_of_day + timedelta(days=1)

        # Filter appointments based on the current date
        queryset = Appointment.objects.filter(
            scheduled_from__gte=start_of_day,
            scheduled_from__lt=end_of_day
        )

        # Exclude appointments with payment_status 'pending'
        queryset = queryset.exclude(
            appointmentstate__payment_status='pending'
        )

        # Include appointments with payment_status 'pending' and appointment_status 'waiting'
        queryset = queryset | Appointment.objects.filter(
            Q(appointmentstate__payment_status='pending') & Q(appointment_status='waiting'),
            scheduled_from__gte=start_of_day,
            scheduled_from__lt=end_of_day
        )

        # Get the clinic and doctor query parameters
        clinic = request.query_params.get('clinic')
        doctor = request.query_params.get('doctor')

        if clinic:
            queryset = queryset.filter(clinic_id=clinic)
        if doctor:
            queryset = queryset.filter(doctor_id=doctor)

        # Filter appointments based on additional query parameters
        # params = self.request.query_params
        # if params and len(params) > 0:
        #     for param in params:
        #         if param not in ['page', 'search', 'clinic', 'doctor']:
        #             queryset = queryset.filter(**{param: params[param]})

        # Count the filtered appointments
        appointments_count = queryset.count()

        # Get count of individual doctors' appointments with their names
        queryset = queryset.values('doctor').annotate(count=Count('doctor'))

        # Prepare data for response
        doctors_data = []
        for doctor_count in queryset:
            doctor_id = doctor_count['doctor']
            doctor = User.objects.get(id=doctor_id)
            doctor_first_name = doctor.first_name
            doctor_last_name = doctor.last_name
            full_name = doctor_first_name + " " + doctor_last_name
            doctor_color = doctor.doctor_calender_color
            doctors_data.append({
                'doctor_id': doctor_id,
                'full_name': full_name,
                'doctor_color': doctor_color,
                'count': doctor_count['count']
            })

        return Response({
            'all': appointments_count,
            'doctors_appointments_count': doctors_data
        })

class PatientCreateAppointment(APIView):

    def validate_data(self, data_object, full_name, email, phone_number):
        errors = {}
        required_fields = ['doctor', 'clinic', 'category', 'scheduled_from', 'scheduled_to']
        for field in required_fields:
            if not data_object.get(field):
                errors[f'{field.capitalize()}Error'] = [f'{field.capitalize()} is required']

        if not full_name:
            errors['FullNameError'] = ['Full name is required']
        if not email:
            errors['EmailError'] = ['Email is required']
        if not phone_number:
            errors['PhoneError'] = ['Phone number is required']

        return errors

    def post(self, request, format=None):
        data_object = request.data
        patient = data_object.pop('patient', None)

        if not patient:
            return Response({
                'state': False,
                'data': {
                    'PatientDataError': ['Patient information is missing']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        email = patient.get('email')
        phone_number = str(patient.get('phone_number', ''))[-10:]
        full_name = patient.get('full_name')

        errors = self.validate_data(data_object, full_name, email, phone_number)
        if errors:
            return Response({
                'state': False,
                'data': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        if email:
            patient_query = Q(email=email)
        if phone_number:
            patient_query &= Q(phone_number__endswith=phone_number)

        try:
            user = User.objects.get(patient_query)
            user_full_name = f"{user.first_name} {user.last_name}".strip()
            if user_full_name.lower() != full_name.lower():
                return Response({
                    'state': False,
                    'data': {
                        'PatientNotFoundError': ['Patient not found. Please use the correct values']
                    }
                }, status=status.HTTP_404_NOT_FOUND)
            if not user:
                raise User.DoesNotExist
            data_object.update({'patient': user.id, 'created_by': user.id, 'updated_by': user.id, 'is_new': False})
        except User.DoesNotExist:

            first_name, last_name = full_name.split(' ', 1) if ' ' in full_name else (full_name, '')
            patient['first_name'] = first_name
            patient['last_name'] = last_name

            user_serializer = UserSerializer(data=patient)
            if user_serializer.is_valid():
                user_data = user_serializer.save()
                user = User.objects.get(pk=user_data.id)
                group = Group.objects.get(pk=settings.PATIENT_GROUP_ID)
                user.groups.add(group)
                user.atlas_id = f"{settings.PREFIX_ATLAS_ID}{user.id}"
                group.user_set.add(user)
                user.save()
                data_object.update({'patient': user_serializer.data['id'], 'created_by': user.id, 'updated_by': user.id, 'is_new': True})
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"User processing error: {e}")
            logger.error(traceback.format_exc())
            return Response({
                'state': False,
                'data': {
                    'Error': [str(e)]
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    

        serializer = AppointmentSerializer(data=data_object, context={'request': request})
        if serializer.is_valid():
            appointment = serializer.save()
            pending_appointment = AppointmentState.objects.create(
                appointment=appointment,
                payment_status='pending'
            )
            data_object.update({'appointment': appointment})
            patient_data = {
                "user_id": data_object["patient"],
                "phone_number": phone_number
            }

            try:
                response = process_payment(patient_data)
                response.raise_for_status()
                response_data = response.json()
                code = response_data.get('code')

                if not response_data.get('success'):
                    pending_appointment.delete()
                    return Response({
                        'state': False,
                        'code': code,
                        'data': {
                            'Error': [response_data["message"]]
                        }
                    }, status=response.status_code)

                if code == 'PAYMENT_INITIATED':

                    cache.set(response_data["data"]["merchantTransactionId"], data_object, 900)

                    return Response({
                        'state': True,
                        'message': response_data["message"],
                        'data': response_data["data"]["instrumentResponse"]["redirectInfo"]
                    }, status=status.HTTP_200_OK)
            except Exception as e:
                pending_appointment.delete()
                logger.error(f"Payment processing error: {e}")
                logger.error(traceback.format_exc())
                return Response({
                    'state': False,
                    'data': {
                        'Error': [str(e)]
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class UpcomingAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        created_by_id = self.request.query_params.get('created_by')
        if not created_by_id:
            raise ValueError('created_by query param is missing')

        try:
            user = User.objects.get(id=created_by_id)
        except User.DoesNotExist:
            raise ValueError('User not found')
    
        return Appointment.objects.filter(
            created_by=user,
            scheduled_from__gte=timezone.now()
        ).exclude(
            Q(appointment_status='cancelled') | Q(appointment_status='checked_out')
        ).order_by('scheduled_from')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
        except ValueError as e:
            return Response({
                'state': False,
                'data': {
                    'Error': [str(e)]
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "state": True,
            "total_appointments": queryset.count(),
            "appointments": serializer.data
        }, status=status.HTTP_200_OK)
    
class BookedSlotsView(APIView):
    def get(self, request):
        try:
            clinic_id = request.query_params.get('clinic_id')
            category_id = request.query_params.get('category_id')
            date_str = request.query_params.get('date')

            if not all([clinic_id, category_id, date_str]):
                return Response({
                    "state": False,
                    "error": "clinic_id, category_id and date are required."
                }, status=status.HTTP_400_BAD_REQUEST)

            clinic = Clinic.objects.get(id=clinic_id)
            category = Category.objects.get(id=category_id)
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()

            if clinic != category.clinic:
                return Response({
                    "state": False,
                    "error": "Clinic name and Category clinic name do not match."
                }, status=status.HTTP_400_BAD_REQUEST)

            doctors = DoctorCategory.objects.filter(
                category__clinic__name=clinic,
                category__name=category.name,
                available_days__name__iexact=date.strftime('%A')
            ).count()

            appointments = Appointment.objects.filter(
                clinic=clinic,
                scheduled_from__date=date,
                appointment_status__in=['booked', 'checked_in', 'engaged']
            )

            slot_counts = {}

            for appointment in appointments:
                scheduled_from = appointment.scheduled_from + timedelta(hours=5, minutes=30)
                scheduled_to = appointment.scheduled_to + timedelta(hours=5, minutes=30)
                slot_key = (appointment.category.name, scheduled_from.time(), scheduled_to.time())

                slot_counts[slot_key] = slot_counts.get(slot_key, 0) + 1  

            result = [
                {
                    "scheduled_from": slot_key[1],
                    "scheduled_to": slot_key[2]
                }
                for slot_key, count in slot_counts.items()
                if slot_key[0] == category.name and count >= doctors
            ]

            return Response({
                "state": True,
                "date": date_str,
                "category_name": category.name,
                "slots": result
            }, status=status.HTTP_200_OK)

        except Clinic.DoesNotExist:
            return Response({
                "state": False,
                "message": "Clinic not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Category.DoesNotExist:
            return Response({
                "state": False,
                "message": "Category not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                "state": False,
                "message": "Invalid date format. Use YYYY-MM-DD."
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "state": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class AppointmentsBookedByPatientsView(APIView):
    def get(self, request):
        try:
            clinic_id = request.query_params.get('clinic_id')

            if not clinic_id:
                return Response({
                    "state": False,
                    "error": "clinic_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            clinic = Clinic.objects.get(id=clinic_id)

            appointments = Appointment.objects.filter(
                clinic=clinic,
                created_by__groups__id=1    # PATIENT = 1
            )
            total = appointments.count()
            
            serializer = AppointmentSerializer(appointments, many=True)
            return Response({
                'state': True,
                'total_appointments': total,
                'appointments': serializer.data
            }, status=status.HTTP_200_OK)  
            
        except Clinic.DoesNotExist:
            return Response({
                "state": False,
                "message": "Clinic not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "state": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BookedDatesView(APIView):
    def get(self, request):
        try:
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            clinic_id = request.query_params.get('clinic_id')
            category_id = request.query_params.get('category_id')

            if not all([from_date, to_date, clinic_id, category_id]):
                return Response({
                    "state": False,
                    "error": "from_date, to_date, clinic_id and category_id are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            clinic = Clinic.objects.get(id=clinic_id)
            category = Category.objects.get(id=category_id)

            if clinic != category.clinic:
                return Response({
                    "state": False,
                    "error": "Clinic name and Category clinic name do not match."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from_date = timezone.datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(to_date, '%Y-%m-%d').date()

            clinic_timings = ClinicTiming.objects.filter(clinic_id=clinic_id, is_available=True)

            if not clinic_timings.exists():
                return Response({
                    "state": False,
                    "error": "No available timings found for the given clinic_id"
                }, status=status.HTTP_404_NOT_FOUND)

            fully_booked_dates = []
            current_date = from_date
            while current_date <= to_date:

                available_doctors = DoctorCategory.objects.filter(
                    category__clinic__name=clinic,
                    category__name=category.name,
                    available_days__name__iexact=current_date.strftime('%A')
                ).count()

                if available_doctors == 0:
                    fully_booked_dates.append(current_date.strftime('%Y-%m-%d'))
                else:    
                    day_timings = clinic_timings.filter(week_day=current_date.strftime('%A').lower())

                    if day_timings.exists():
                        for timing in day_timings:
                            start_time = timezone.make_aware(timezone.datetime.combine(current_date, timing.start_at))
                            end_time = timezone.make_aware(timezone.datetime.combine(current_date, timing.end_at))

                            total_minutes = self.calculate_available_minutes(timing, start_time, end_time)
                            slot_duration = 15
                            total_slots = int(total_minutes / slot_duration)

                            booked_appointments = Appointment.objects.filter(
                                clinic_id=clinic_id,
                                scheduled_from__date=current_date,
                                scheduled_from__gte=start_time,
                                scheduled_to__lte=end_time
                            ).count()

                            if booked_appointments >= total_slots:
                                fully_booked_dates.append(current_date.strftime('%Y-%m-%d'))
                                break
                            
                current_date += timedelta(days=1)

            return Response({
                "state": True,
                "booked_dates": fully_booked_dates
            }, status=status.HTTP_200_OK)
        except Clinic.DoesNotExist:
            return Response({
                "state": False,
                "message": "Clinic not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Category.DoesNotExist:
            return Response({
                "state": False,
                "message": "Category not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                "state": False,
                "message": "Invalid date format. Use YYYY-MM-DD."
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "state": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calculate_available_minutes(self, timing, start_time, end_time):
        try:
            total_minutes = (end_time - start_time).total_seconds() / 60

            if timing.break_1_start and timing.break_1_end:
                break_1_start = timezone.make_aware(timezone.datetime.combine(start_time.date(), timing.break_1_start))
                break_1_end = timezone.make_aware(timezone.datetime.combine(start_time.date(), timing.break_1_end))
                break_1_duration = (break_1_end - break_1_start).total_seconds() / 60
                total_minutes -= break_1_duration

            if timing.break_2_start and timing.break_2_end:
                break_2_start = timezone.make_aware(timezone.datetime.combine(start_time.date(), timing.break_2_start))
                break_2_end = timezone.make_aware(timezone.datetime.combine(start_time.date(), timing.break_2_end))
                break_2_duration = (break_2_end - break_2_start).total_seconds() / 60
                total_minutes -= break_2_duration

            return max(total_minutes, 0)

        except Exception as e:
            return 0
        
class AvailableDoctorsView(APIView):
    def get(self, request):
        try:
            clinic_id = request.query_params.get('clinic_id')
            category_id = request.query_params.get('category_id')
            scheduled_from = request.query_params.get('scheduled_from')
            scheduled_to = request.query_params.get('scheduled_to')

            if not all([clinic_id, category_id, scheduled_from, scheduled_to]):
                return Response({
                    'error': 'clinic_id , category_id, scheduled_from and scheduled_to are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            clinic = Clinic.objects.get(id=clinic_id)
            category = Category.objects.get(id=category_id)

            date_str = (
                datetime.fromisoformat(scheduled_from.replace("Z", "+00:00")) +
                timedelta(hours=5, minutes=30)
            ).strftime("%Y-%m-%d")
            
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()

            if clinic != category.clinic:
                return Response({
                    "state": False,
                    "error": "Clinic name and Category clinic name do not match."
                }, status=status.HTTP_400_BAD_REQUEST)

            doctors = [
                dc.doctor for dc in DoctorCategory.objects.filter(
                    category__clinic__name=clinic.name,
                    category__name=category.name,
                    available_days__name__iexact=date.strftime('%A')
                )
            ]

            scheduled_from = datetime.strptime(scheduled_from, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
            scheduled_to = datetime.strptime(scheduled_to, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
            date = scheduled_from.date()
            
            busy_doctors = Appointment.objects.filter(
                clinic=clinic,
                category=category,
                scheduled_from__date=date,
                scheduled_from__lte=scheduled_to,
                scheduled_to__gte=scheduled_from,
                appointment_status__in=['booked', 'checked_in', 'engaged']
            ).values_list('doctor_id', flat=True)

            final_available_doctors = [
                doctor for doctor in doctors 
                if doctor.id not in busy_doctors
            ]
            serialized_doctors = AvailableDoctorSerializer(final_available_doctors, many=True).data
            for doctor in serialized_doctors:
                doctor['name'] = doctor.pop('full_name')
            
            return Response({
                "state": True,
                'doctors': serialized_doctors
            }, status=status.HTTP_200_OK)   

        except Clinic.DoesNotExist:
            return Response({
                "state": False,
                "message": "Clinic not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Category.DoesNotExist:
            return Response({
                "state": False,
                "message": "Category not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                "state": False,
                "message": "Invalid date format. Use YYYY-MM-DD."
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "state": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class AppointmentPaymentStatus(APIView):
    def get(self, request, appointment_id):
        try:
            if not appointment_id:
                raise ValueError("Appointment ID is required")

            appointment_state = AppointmentState.objects.get(appointment_id=appointment_id)
            return Response({
                "state": True,
                "appointment_id": appointment_id,
                "payment_status": appointment_state.payment_status
            }, status=status.HTTP_200_OK)

        except AppointmentState.DoesNotExist:
            return Response({
                "state": False,
                "error": "Appointment not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError as ve:
            return Response({
                "state": False,
                "error": str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "state": False,
                "error": "An unexpected error occurred",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppointmentStatus(APIView):
    def post(self, request, appointment_id):
        try:
            if not appointment_id:
                raise ValueError("Appointment ID is required")

            appointment = Appointment.objects.get(id=appointment_id)
            appointment.appointment_status = 'waiting'
            appointment.save()

            return Response({
                "state": True,
                "appointment_id": appointment_id,
                "appointment_status": appointment.appointment_status
            }, status=status.HTTP_200_OK)

        except Appointment.DoesNotExist:
            return Response({
                "state": False,
                "error": "Appointment not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError as ve:
            return Response({
                "state": False,
                "error": str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "state": False,
                "error": "An unexpected error occurred",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)