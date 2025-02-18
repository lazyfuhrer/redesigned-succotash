# Create your views here.
import logging
import traceback
from datetime import timedelta
from django.utils import timezone

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.models import Q, Value, Case, When, IntegerField, F
from django.db.models.functions import Lower
from knox.models import AuthToken
from rest_framework import permissions, generics, filters, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models.functions import Concat

from clinic.serializers import ClinicPeopleSerializer
from fuelapp.pagination import CustomPagination
from .models import User, Address, DoctorTiming, Leaves, Otp
from .serializers import LoginUserSerializer, AddressSerializer, \
    ForgetPasswordSerializer, CreateUserSerializer, UserSerializer, \
    DoctorTimingSerializer, LeaveSerializer, DoctorSerializer, \
    StaffSerializer, PatientInfoSerializer
from .utils import send_verify_code, gen_rand_code, generate_otp, mask_name
from base.helpers.sms import SMSUtils
from base.helpers.email import EmailUtils

logger = logging.getLogger('fuelapp')

class RegistrationAPI(generics.GenericAPIView):
    serializer_class = CreateUserSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user,
                                   context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })

class LoginAPI(generics.GenericAPIView):
    serializer_class = LoginUserSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        user.auth_token_set.all().delete()
        return Response({
            "user": UserSerializer(user,
                                   context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })


class ForgetPasswordAPI(generics.UpdateAPIView):
    """
    An endpoint for changing password.
    """
    serializer_class = ForgetPasswordSerializer
    permission_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        user.auth_token_set.all().delete()
        return Response({
            "Your password has changed"
        })


class ResendCode(APIView):
    def post(self, request, format=None):
        try:
            email = request.data.get('email', '')
            user = User.objects.get(email=email, email_verified=False)
            user.email_code = gen_rand_code()
            user.save()
            send_verify_code(user)
            response = {'status': 'success',
                        'message': 'Email verification code resent',
                        'code': status.HTTP_200_OK}
            return Response(response)
        except ObjectDoesNotExist:
            logger(traceback.format_exc())
            return Response({'status': 'error',
                             'message': 'user not found / already verified'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger(traceback.format_exc())
            return Response({'status': 'error'},
                            status=status.HTTP_400_BAD_REQUEST)


class Verify(APIView):
    def post(self, request, format=None):
        try:
            data = request.data
            email = data.get('email', '')
            code = data.get('code', '')
            # logger(data)
            user = User.objects.get(
                email=email, email_code=code, email_verified=0)
            if user:
                # user.email_code = ""
                user.email_verified = 1
                user.save()
                response = {'status': 'success',
                            'message': 'Email verified',
                            'code': status.HTTP_200_OK}
                return Response(response)
        except ObjectDoesNotExist:
            logger(traceback.format_exc())
            return Response({'status': 'error',
                             'message': 'user not found / already verified'},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger(traceback.format_exc())
            return Response({'status': 'error'},
                            status=status.HTTP_400_BAD_REQUEST)


class TestEmail(APIView):
    def get(self, request, format=None):
        try:
            message = "Hello World"
            is_success = send_mail(
                # title:
                subject="Password Reset for {title}".format(
                    title="Atlas Chiropractic & Wellness"),
                # message:
                message=message,
                # from:
                from_email=settings.DEFAULT_FROM_EMAIL,
                # to:
                # ,'abdul.nazurudeen@gmail.com'
                recipient_list=['2minstudio.dev@gmail.com']

            )
        except Exception as ex:
            logger(f'{ex}')
            logger(traceback.format_exc())
        response = {'status': 'okay'}
        return Response(response)


class UserAPI(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by(Lower('first_name'))
    serializer_class = UserSerializer
    # filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', '^email', '^phone_number', 'atlas_id']
    ordering_fields = ['first_name']

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        # serializer.save(created_by=self.request.user,
        #               updated_by=self.request.user)
        serializer.save()

    def get_queryset(self):
        queryset = User.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})

        search_query = params.get('search', '')
        if search_query:
            # Concatenate first_name and last_name for searching
            queryset = queryset.annotate(
                full_name=Concat(F('first_name'), Value(' '), F('last_name'))
            ).filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(atlas_id__icontains=search_query)
            )

            # Prioritize names starting with the search query
            queryset = queryset.annotate(
                starts_with_full_name=Case(
                    When(full_name__istartswith=search_query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).order_by(
                '-starts_with_full_name',
                Lower('first_name')
            )

        return queryset

class UserView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_update(self, serializer):
        # Set updated_by field
        instance = serializer.save(updated_by=self.request.user)
        photo_file = self.request.data.get('photo')
        if photo_file:
            instance.photo = photo_file
            instance.save()


class AddressList(generics.ListCreateAPIView):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Address.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class AddressView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class DoctorTimingList(generics.ListCreateAPIView):
    queryset = DoctorTiming.objects.all()
    serializer_class = DoctorTimingSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = DoctorTiming.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class DoctorTimingView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DoctorTiming.objects.all()
    serializer_class = DoctorTimingSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class LeavesList(generics.ListCreateAPIView):
    queryset = Leaves.objects.all()
    serializer_class = LeaveSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Leaves.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class LeavesView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Leaves.objects.all()
    serializer_class = LeaveSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)

class LeavesListView(generics.ListAPIView):
    serializer_class = LeaveSerializer
    
    def get_queryset(self):
        clinic = self.request.query_params.get('clinic')
        scheduled_from = self.request.query_params.get('scheduled_from')
        scheduled_to = self.request.query_params.get('scheduled_to')

        # Filter queryset by the selected date range
        queryset = Leaves.objects.all().order_by('scheduled_from')

        if clinic:
            queryset = queryset.filter(clinic=clinic)
        if scheduled_from:
            queryset = queryset.filter(scheduled_from=scheduled_from)
        if scheduled_to:
            queryset = queryset.filter(scheduled_to=scheduled_to)

        return queryset


class DoctorList(generics.ListCreateAPIView):
    group_id = 2
    queryset = User.objects.filter(groups=group_id)
    pagination_class = CustomPagination
    serializer_class = DoctorSerializer

    # parser_classes = (MultiPartParser, FormParser)
    def get_queryset(self):
        queryset = self.queryset
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param == 'clinic':
                    queryset = queryset.filter(
                        clinicpeople__clinic__in=[params[param]])
                elif param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})

        return queryset

    def create(self, request, *args, **kwargs):
        # doctor_serializer = DoctorSerializer(data=request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        try:
            doctor.groups.add(self.group_id)
            clinic_id = request.data.get('clinic')
            clinic_people_data = {"user": doctor.id, "clinic": clinic_id,
                                  "created_by": request.user.id,
                                  "updated_by": request.user.id}

            clinic_people_serializer = ClinicPeopleSerializer(
                data=clinic_people_data)
            clinic_people_serializer.is_valid(raise_exception=True)
            clinic_people_serializer.save()

        except Exception as e:
            print(e)
            return Response(
                {'error': 'An error occurred during user creation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DoctorView(generics.RetrieveUpdateDestroyAPIView):
    group_id = 2
    queryset = User.objects.filter(groups=group_id)
    serializer_class = DoctorSerializer
    parser_classes = (MultiPartParser, FormParser)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data,
                                         partial=True)

        # Check if 'file_field' exists in the request data
        if 'signature' in request.data:
            # A file is provided in the request, update it
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        else:
            # No file provided in the request, don't update the file field
            serializer.is_valid(raise_exception=True)
            serializer.save(signature=instance.signature)
            return Response(serializer.data)

    # def perform_update(self, serializer):
    #     # Set updated_by field
    #     instance = serializer.save(updated_by=self.request.user)
    #     signature_file = self.request.data.get('signature')
    #     if signature_file:
    #         instance.signature = signature_file
    #         instance.save()


class StaffList(generics.ListCreateAPIView):
    group_id = 3
    queryset = User.objects.filter(groups=group_id)
    pagination_class = CustomPagination
    serializer_class = StaffSerializer

    def create(self, request, *args, **kwargs):
        # doctor_serializer = DoctorSerializer(data=request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        try:
            staff.groups.add(self.group_id)
            clinic_id = request.data.get('clinic')
            clinic_people_data = {"user": staff.id, "clinic": clinic_id,
                                  "created_by": request.user.id,
                                  "updated_by": request.user.id}

            clinic_people_serializer = ClinicPeopleSerializer(
                data=clinic_people_data)
            clinic_people_serializer.is_valid(raise_exception=True)
            clinic_people_serializer.save()

        except Exception as e:
            return Response(
                {'error': 'An error occurred during user creation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StaffView(generics.RetrieveUpdateDestroyAPIView):
    group_id = 3
    queryset = User.objects.filter(groups=group_id)
    serializer_class = StaffSerializer
        
class PatientRegisterAPI(generics.GenericAPIView):
    permission_classes = []

    def post(self, request):
        patient_type = request.query_params.get('type')
        auth = request.query_params.get('auth')

        if not patient_type:
            return Response({
                'state': False,
                'data': {
                    'QueryParamError': ['"type" query param not found']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if patient_type not in ['new', 'old']:
            return Response({
                'state': False,
                'data': {
                    'QueryParamError': ['"type" query param must be either "new" or "old"']
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if patient_type=="old":
            if not auth:
                return Response({
                    'state': False,
                    'data': {
                        'QueryParamError': ['"auth" query param not found']
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
        
            if auth not in ['email', 'phone']:
                return Response({
                    'state': False,
                    'data': {
                        'QueryParamError': ['"auth" query param must be either "email" or "phone"']
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name', '')
        email = request.data.get('email')
        phone_number = str(request.data.get('phone_number', ''))[-10:]

        errors = {}

        if not first_name:
            errors['FirstNameError'] = ['First name is required']  
        if patient_type == 'new':
            if not email:
                errors['EmailError'] = ['Email is required']
            if not phone_number:
                errors['PhoneError'] = ['Phone number is required']
        else:
            if auth == 'email':
                if not email:
                    errors['EmailError'] = ['Email is required']
            else:
                if not phone_number:
                    errors['PhoneError'] = ['Phone number is required']

        if errors:
            return Response({
                'state': False,
                'data': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if patient_type == 'new':
                serializer = PatientInfoSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response({
                        'state': False,
                        'data': {
                            'ValidationError': serializer.errors
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

                if User.objects.filter(Q(email=email)).exists():
                    return Response({
                        'state': False,
                        'data': {
                            'EmailExistsError': ['Patient with this email already exists. Please use another email.']
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                if User.objects.filter(Q(phone_number__endswith=phone_number)).exists():
                    return Response({
                        'state': False,
                        'data': {
                            'PhoneExistsError': ['Patient with this phone number already exists. Please use another phone number.']
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

                user = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    username=email,
                    phone_number="+91" + phone_number
                )
                user.atlas_id = f"A{user.id}"
                user.save()
                user.groups.add(1)  # PATIENT = 1

                otp = generate_otp()
                otp_obj, created = Otp.objects.update_or_create(
                    user=user,
                    defaults={
                        'otp': otp,
                        'is_used': False,
                        'attempts': 0,
                        'created_at': timezone.now(),
                        'expires_at': timezone.now() + timedelta(minutes=10)
                    }
                )
                data = {
                    'first_name': user.first_name,
                    'otp_code': otp
                }
                sms_utils = SMSUtils('confirmation_code')
                sms_utils.send(user.phone_number[-10:], data)
                EmailUtils(user.email, "OTP Code", 'confirmation-code', data).send()
                otp_obj.sent_at = timezone.now()
                otp_obj.save()

                return Response({
                    'state': True,
                    'message': 'OTP sent successfully. Please check your registered email and phone number.',
                    'data': {
                        'user': UserSerializer(user, context=self.get_serializer_context()).data
                    }
                }, status=status.HTTP_201_CREATED)
            
            else:
                if email:
                    patient_query = Q(email=email)
                else:
                    patient_query = Q(phone_number__endswith=phone_number)    
                user = User.objects.filter(patient_query).first()

                if user.first_name.lower() != first_name.lower() or (last_name and user.last_name.lower() != last_name.lower()):
                    masked_first_name = mask_name(user.first_name)
                    masked_last_name = mask_name(user.last_name) if user.last_name else ''
                    return Response({
                        'state': False,
                        'data': {
                            'NameMismatchError': [f'Name not found. Please enter registered name. Hint: {masked_first_name} {masked_last_name}']
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

                if user:
                    if not user.groups.filter(id=1).exists():
                        return Response({
                            'state': False,
                            'data': {
                                'Error': ['User is not a patient'],
                            }
                        }, status=status.HTTP_403_FORBIDDEN)
                    if not user.atlas_id:
                        user.atlas_id = f"A{user.id}"    
                        user.save()

                    otp = generate_otp()
                    otp_obj, created = Otp.objects.update_or_create(
                        user=user,
                        defaults={
                            'otp': otp,
                            'is_used': False,
                            'attempts': 0,
                            'created_at': timezone.now(),
                            'expires_at': timezone.now() + timedelta(minutes=10)
                        }
                    )
                    data = {
                        'first_name': user.first_name,
                        'otp_code': otp
                    }

                    if auth == 'email':
                        EmailUtils(user.email, "OTP Code", 'confirmation-code', data).send()
                        otp_obj.sent_at = timezone.now()
                        otp_obj.save()

                        return Response({
                            'state': True,
                            'message': 'OTP sent successfully. Please check your registered email',
                            'data': {
                                'user': UserSerializer(user, context=self.get_serializer_context()).data,
                            }
                        }, status=status.HTTP_200_OK)

                    else:
                        sms_utils = SMSUtils('confirmation_code')
                        response = sms_utils.send(user.phone_number[-10:], data)
                        otp_obj.sent_at = timezone.now()
                        otp_obj.save()

                        if response:
                            return Response({
                                'state': True,
                                'message': 'OTP sent successfully. Please check your registered phone number',
                                'data': {
                                    'user': UserSerializer(user, context=self.get_serializer_context()).data,
                                }
                            }, status=status.HTTP_200_OK)

                        else:
                            return Response({
                                'state': False,
                                'data': {
                                    'SmsSendError': ['Failed to send SMS'],
                                }
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                else:
                    patient_qr = Q(first_name__iexact=first_name)
                    if last_name:
                        patient_qr &= Q(last_name__iexact=last_name)   
                    patient = User.objects.filter(patient_qr).first()

                    if patient:
                        if not patient.groups.filter(id=1).exists():
                            return Response({
                                'state': False,
                                'data': {
                                    'Error': ['User is not a patient'],
                                }
                            }, status=status.HTTP_403_FORBIDDEN)
                        if not patient.atlas_id:
                            patient.atlas_id = f"A{patient.id}"    
                            patient.save()

                        otp = generate_otp()
                        otp_obj, created = Otp.objects.update_or_create(
                            user=patient,
                            defaults={
                                'otp': otp,
                                'is_used': False,
                                'attempts': 0,
                                'created_at': timezone.now(),
                                'expires_at': timezone.now() + timedelta(minutes=10)
                            }
                        )
                        data = {
                            'first_name': patient.first_name,
                            'otp_code': otp
                        }    

                        if auth == "email":
                            if patient.email:
                                return Response({
                                    'state': False,
                                    'data': {
                                        'EmailNotRegisteredError': ['Email ID is not registered. Please enter the registered email ID']
                                    }
                                }, status=status.HTTP_400_BAD_REQUEST)

                            if User.objects.filter(email__iexact=email).exists():
                                return Response({
                                    'state': False,
                                    'data': {
                                        'EmailExistsError': ['Patient with this email already exists. Please use another email.']
                                    }
                                }, status=status.HTTP_400_BAD_REQUEST)

                            patient.email = email
                            patient.save()
                            
                            EmailUtils(patient.email, "OTP Code", 'confirmation-code', data).send()
                            otp_obj.sent_at = timezone.now()
                            otp_obj.save()

                            return Response({
                                'state': True,
                                'message': 'OTP sent successfully. Please check your updated email.',
                                'data': {
                                    'user': UserSerializer(patient, context=self.get_serializer_context()).data,
                                }
                            }, status=status.HTTP_200_OK)
                        else:
                            if patient.phone_number:
                                return Response({
                                    'state': False,
                                    'data': {
                                        'PhoneNotRegisteredError': ['Phone number is not registered. Please enter the registered phone number']
                                    }
                                }, status=status.HTTP_400_BAD_REQUEST)
                            if User.objects.filter(phone_number__endswith=phone_number).exists():
                                return Response({
                                    'state': False,
                                    'data': {
                                        'PhoneExistsError': ['Patient with this phone number already exists. Please use another phone number.']
                                    }
                                }, status=status.HTTP_400_BAD_REQUEST)

                            patient.phone_number = '+91' + phone_number
                            patient.save()

                            sms_utils = SMSUtils('confirmation_code')
                            response = sms_utils.send(patient.phone_number[-10:], data)
                            otp_obj.sent_at = timezone.now()
                            otp_obj.save()

                            if response:
                                return Response({
                                    'state': True,
                                    'message': 'OTP sent successfully. Please check your updated phone number.',
                                    'data': {
                                        'user': UserSerializer(patient, context=self.get_serializer_context()).data,
                                    }
                                }, status=status.HTTP_200_OK)
                    else:
                        return Response({
                            'state': False,
                            'data': {
                                'PatientNotFoundError': ['Patient not found. Please use the correct values']
                            }
                        }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(traceback.format_exc())
            return Response({
                'state': False,
                'data': {
                    'InternalError': [str(e)]
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PatientVerifyOtpAPI(generics.GenericAPIView):
    permission_classes = []

    def post(self, request):
        auth = request.query_params.get('auth')
        email = request.data.get('email')
        phone_number = str(request.data.get('phone_number', ''))[-10:]
        otp = request.data.get('otp')

        if not auth:
            return Response({
                'state': False,
                'data': {
                    'QueryParamError': ['"auth" query param not found']
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if auth not in ['email', 'phone']:
            return Response({
                'state': False,
                'data': {
                    'QueryParamError': ['"auth" query param must be either "email" or "phone"']
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        errors = {}

        if not otp:
            errors['OtpError'] = ['OTP is required']
        if auth == 'email' and not email:
            errors['EmailError'] = ['Email is required']
        if auth == 'phone' and not phone_number:
            errors['PhoneError'] = ['Phone number is required']

        if errors:
            return Response({
                'state': False,
                'data': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if auth == 'email':
                user = User.objects.get(email=email)
            else:
                user = User.objects.get(phone_number__endswith=phone_number)
        except User.DoesNotExist:
            return Response({
                'state': False,
                'data': {
                    'PatientNotFoundError': ['Patient not found. Please use the correct values']
                }
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            otp_obj = Otp.objects.get(user=user, otp=otp)
        except Otp.DoesNotExist:
            return Response({
                'state': False,
                'data': {
                    'InvalidOtpError': ['Invalid OTP']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # if otp_obj.is_used:
        #     return Response({
        #         'state': False,
        #         'data': {
        #             'UsedOtpError': ['OTP has already been used']
        #         }
        #     }, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.expires_at < timezone.now():
            new_otp = generate_otp()
            otp_obj.otp = new_otp
            otp_obj.is_used = False
            otp_obj.attempts = 0
            otp_obj.created_at = timezone.now()
            otp_obj.expires_at = timezone.now() + timedelta(minutes=10)
            otp_obj.sent_at = timezone.now()
            otp_obj.save()

            data = {
                'first_name': user.first_name,
                'otp_code': new_otp
            }
            if auth == 'email':
                EmailUtils(user.email, "OTP Code", 'confirmation-code', data).send()
            else:
                sms_utils = SMSUtils('confirmation_code')
                sms_utils.send(user.phone_number[-10:], data)

            otp_obj.sent_at = timezone.now()
            return Response({
                'state': True,
                'message': 'OTP has expired. A new OTP has been sent to your registered email and phone number.',
                'data': {
                    'user': UserSerializer(user, context=self.get_serializer_context()).data
                }
            }, status=status.HTTP_200_OK)

        otp_obj.is_used = True
        otp_obj.save()

        user.auth_token_set.all().delete()

        return Response({
            'state': True,
            'message': 'OTP verified successfully.',
            'data': {
                'user': UserSerializer(user, context=self.get_serializer_context()).data,
                'token': AuthToken.objects.create(user)[1]
            }
        }, status=status.HTTP_200_OK)
    
class PatientLoginAPI(generics.GenericAPIView):
    permission_classes = []

    def post(self, request):
        auth = request.query_params.get('auth')
        resend_otp = request.query_params.get('resend_otp', 'false').lower() == 'true'

        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name', '')
        email = request.data.get('email')
        phone_number = str(request.data.get('phone_number', ''))[-10:]

        if not auth:
            return Response({
                'state': False,
                'data': {
                    'QueryParamError': ['"auth" query param not found']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if auth not in ['email', 'phone']:
            return Response({
                'state': False,
                'data': {
                    'QueryParamError': ['"auth" query param must be either "email" or "phone"']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        errors = {}

        if not first_name:
            errors['FirstNameError'] = ['First name is required']
        if auth == 'email' and not email:
            errors['EmailError'] = ['Email is required']
        if auth == 'phone' and not phone_number:
            errors['PhoneError'] = ['Phone number is required']

        if errors:
            return Response({
                'state': False,
                'data': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if auth == 'email':
                patient_query = Q(email=email)
            else:
                patient_query = Q(phone_number__endswith=phone_number)
            user = User.objects.filter(patient_query).first()
        except User.DoesNotExist:
            return Response({
                'state': False,
                'data': {
                    'PatientNotFoundError': ['Patient not found. Please use the correct values']
                }
            }, status=status.HTTP_404_NOT_FOUND)

        if user.first_name.lower() != first_name.lower() or (last_name and user.last_name.lower() != last_name.lower()):
            masked_first_name = mask_name(user.first_name)
            masked_last_name = mask_name(user.last_name) if user.last_name else ''
            return Response({
                'state': False,
                'data': {
                    'NameMismatchError': [f'Name not found. Please enter registered name. Hint: {masked_first_name} {masked_last_name}']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_obj = Otp.objects.filter(user=user).first()
        if otp_obj and resend_otp:
            time_diff = timezone.now() - otp_obj.sent_at
            if time_diff < timedelta(seconds=30):
                return Response({
                    'state': False,
                    'data': {
                        'ResendOtpError': ['You can resend OTP after 30 seconds']
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        otp = generate_otp()
        otp_obj, created = Otp.objects.update_or_create(
            user=user,
            defaults={
                'otp': otp,
                'is_used': False,
                'attempts': 0,
                'created_at': timezone.now(),
                'expires_at': timezone.now() + timedelta(minutes=10)
            }
        )
        data = {
            'first_name': user.first_name,
            'otp_code': otp
        }

        if auth == 'email':
            EmailUtils(user.email, "OTP Code", 'confirmation-code', data).send()
            otp_obj.sent_at = timezone.now()
            otp_obj.save()

            return Response({
                'state': True,
                'message': 'OTP sent successfully. Please check your registered email.',
                'data': {
                    'user': UserSerializer(user, context=self.get_serializer_context()).data,
                }
            }, status=status.HTTP_200_OK)

        else:
            sms_utils = SMSUtils('confirmation_code')
            sms_utils.send(user.phone_number[-10:], data)
            otp_obj.sent_at = timezone.now()
            otp_obj.save()

            return Response({
                'state': True,
                'message': 'OTP sent successfully. Please check your registered phone number.',
                'data': {
                    'user': UserSerializer(user, context=self.get_serializer_context()).data,
                }
            }, status=status.HTTP_200_OK)

class PatientProfileUpdateAPI(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PatientInfoSerializer
    
    def get_object(self):
        return self.request.user
        
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Check if user is a patient (group_id = 1)
        if not user.groups.filter(id=1).exists():
            return Response({
                'state': False,
                'data': {
                    'Error': ['Only patients can update their profile']
                }
            }, status=status.HTTP_403_FORBIDDEN)

        # Get the data from request
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')
        
        if phone_number:
            phone_number = str(phone_number)[-10:]  # Get last 10 digits
            
        # Validate email uniqueness if email is being updated
        if email and email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({
                    'state': False,
                    'data': {
                        'EmailError': ['This email is already registered with another account']
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
                
        # Validate phone number uniqueness if phone is being updated 
        if phone_number and phone_number != user.phone_number[-10:]:
            if User.objects.filter(phone_number__endswith=phone_number).exclude(id=user.id).exists():
                return Response({
                    'state': False,
                    'data': {
                        'PhoneError': ['This phone number is already registered with another account']
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        # Update the user profile
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            if phone_number:
                serializer.save(phone_number='+91' + phone_number)
            else:
                serializer.save()
                
            return Response({
                'state': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        return Response({
            'state': False,
            'data': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)            