from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from rest_framework import serializers

from .models import User, Address, DoctorTiming, Leaves


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password', 'phone_number',
                  'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(validated_data['email'],
                                        validated_data['email'],
                                        validated_data['password'],
                                        phone_number=validated_data[
                                            'phone_number'],
                                        first_name=validated_data[
                                            'first_name'],
                                        last_name=validated_data['last_name'])
        return user


class UserSerializer(serializers.ModelSerializer):
    # email = serializers.EmailField(required=True)
    address = serializers.SerializerMethodField(read_only=True)
    wallet_balance = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    clinics = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'photo', 'first_name', 'last_name',
                  'phone_number', 'gender', 'date_of_birth', 'blood_group',
                  'signature', 'groups', 'user_permissions', 'permissions',
                  'address', 'wallet_balance', 'full_name', 'clinics',
                  'referred_by_source', 'atlas_id', 'family')
        # , 'referred_by'
        extra_kwargs = {'first_name': {
            'required': True}}

        # validators = []

    # Skipped to check email uniqueness due to patients can have same email
    # def validate_email(self, value):
    #     """
    #     Custom validation to check uniqueness of email.
    #     """
    #     if User.objects.filter(email=value).exists():
    #         raise serializers.ValidationError('Email address already exists.')
    #     return value

    def validate_phone_number(self, value):
        if not value.startswith('+91'):
            value = '+91' + value
        return value

    def get_address(self, obj):
        address = Address.objects.filter(user=obj)
        return AddressSerializer(address, many=True).data

    def get_wallet_balance(self, obj):
        from payment.utils import get_user_wallet_balance
        return get_user_wallet_balance(obj.id)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_permissions(self, obj):
        # Get the user's group-assigned permissions
        group_permissions = Permission.objects.filter(group__user=obj)

        # Get the user's individual permissions
        user_permissions = obj.user_permissions.all()

        # Combine and serialize the permissions
        combined_permissions = group_permissions | user_permissions
        return [permission.codename for permission in combined_permissions]

    def get_clinics(self, obj):
        from clinic.models import ClinicPeople
        clinics = ClinicPeople.objects.filter(
            user=obj
        ).first()
        from clinic.serializers import ClinicPeopleSerializer
        return ClinicPeopleSerializer(clinics).data  # clinics


class LoginUserSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        user = authenticate(request=self.context.get('request'),
                            email=email, password=password)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid Details.")


class ForgetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        new_password = data.get('new_password')
        user = authenticate(request=self.context.get('request'),
                            password=new_password)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid Details.")


class AddressSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Address
        fields = (
            'id',
            'user',
            'type',
            'address_line_1',
            'address_line_2',
            'city',
            'country',
            'state',
            'pin_code',
            'phone_no_1',
            'phone_no_2',
            'full_address',
        )

    def get_full_address(self, obj):
        return "{}, {}, {}, {}, {} - {}".format(obj.address_line_1,
                                                obj.address_line_2, obj.city,
                                                obj.state, obj.country,
                                                obj.pin_code)


class DoctorTimingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorTiming
        fields = (
            'id',
            'user',
            'week_day',
            'start_at',
            'break_1_start',
            'break_1_end',
            'break_2_start',
            'break_2_end',
            'end_at',
            'is_available',
        )


class LeaveSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Leaves
        fields = [
            'id',
            'user',
            'doctor_name',
            'clinic',
            'scheduled_from',
            'scheduled_to',
            'leave_note',
            'created_by',
            'updated_by'
        ]

    def get_doctor_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class DoctorSerializer(serializers.ModelSerializer):
    signature = serializers.ImageField(required=False)
    full_name = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True, required=True)

    # doctor_calender_color = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'password', 'full_name',
                  'email', 'phone_number', 'gender', 'signature',
                  'doctor_calender_color']

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password'))
        return super(DoctorSerializer, self).create(validated_data)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def validate_signature(self, value):
        # Check if a file is provided in the request
        if not self.context['request'].FILES.get('signature'):
            # No file is provided, so we don't require validation
            return value

        # If a file is provided, validate it
        if not value:
            raise serializers.ValidationError("Signature is required.")
        return value


class StaffSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email',
                  'gender', 'password', 'phone_number']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password'))
        return super(StaffSerializer, self).create(validated_data)


class PatientInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)
    address = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email',
                  'gender', 'phone_number', 'address', 'atlas_id']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
