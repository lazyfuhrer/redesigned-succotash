from rest_framework import serializers

from user.models import User
from .models import Clinic, ClinicPeople, ClinicTiming, ClinicDay


class ClinicSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Clinic
        fields = (
            'id',
            'logo',
            'name',
            'tagline',
            'full_address',
            'address_line_1',
            'address_line_2',
            'city',
            'country',
            'state',
            'pincode',
            'email',
            'phone_no_1',
            'phone_no_2',
            'website',
            'map_link',
            'review_link',
            'slot_duration',
        )

    def get_full_address(self, obj):
        return "{}, {}, {}, {}, {} - {}".format(obj.address_line_1,
                                                obj.address_line_2, obj.city,
                                                obj.state, obj.country,
                                                obj.pincode)


class ClinicPeopleSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    clinic = serializers.PrimaryKeyRelatedField(queryset=Clinic.objects.all(),
                                                many=True)

    class Meta:
        model = ClinicPeople
        fields = (
            'id',
            'clinic',
            'user',
            'created_by',
            'updated_by',
        )


class ClinicTimingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicTiming
        fields = (
            'id',
            'clinic',
            'week_day',
            'start_at',
            'break_1_start',
            'break_1_end',
            'break_2_start',
            'break_2_end',
            'end_at',
            'is_available',
            'created_by',
            'updated_by',
        )


class ClinicTimingListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        timings = [ClinicTiming.objects.create(**item) for item in
                   validated_data if 'id' not in item]
        return timings

    def update(self, instance, validated_data):
        timing_mapping = {timing.id: timing for timing in instance}
        data_mapping = {item['id']: item for item in validated_data if 'id'
                        in item}

        ret = []
        for timing_id, data in data_mapping.items():
            timing = timing_mapping.get(timing_id, None)
            if timing is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(timing, data))

        for new_data in validated_data:
            if 'id' not in new_data:
                ret.append(self.child.create(new_data))

        return ret


class ClinicTimingMultipleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # Add this line

    class Meta:
        model = ClinicTiming
        fields = ['id', 'clinic', 'week_day', 'start_at', 'break_1_start',
                  'break_1_end', 'break_2_start', 'break_2_end', 'end_at',
                  'is_available', 'end_at', 'created_by', 'updated_by']
        list_serializer_class = ClinicTimingListSerializer

    def update(self, instance, validated_data):
        instance.week_day = validated_data.get('week_day', instance.week_day)
        instance.start_at = validated_data.get('start_at', instance.start_at)
        instance.end_at = validated_data.get('end_at', instance.end_at)
        instance.break_1_start = validated_data.get('break_1_start',
                                                    instance.break_1_start)
        instance.break_1_end = validated_data.get('break_1_end',
                                                  instance.break_1_end)
        instance.break_2_start = validated_data.get('break_2_start',
                                                    instance.break_2_start)
        instance.break_2_end = validated_data.get('break_2_end',
                                                  instance.break_2_end)
        instance.is_available = validated_data.get('is_available',
                                                   instance.is_available)
        instance.save()
        return instance

class ClinicDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicDay
        fields = ['id', 'name']