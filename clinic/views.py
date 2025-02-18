from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Clinic, ClinicPeople, ClinicTiming
from .serializers import ClinicSerializer, ClinicPeopleSerializer, \
    ClinicTimingSerializer, ClinicTimingMultipleSerializer

# Create your views here.
User = get_user_model()


class ClinicList(generics.ListCreateAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = Clinic.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class ClinicView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class ClinicPeopleList(generics.ListCreateAPIView):
    queryset = ClinicPeople.objects.all()
    serializer_class = ClinicPeopleSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = ClinicPeople.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class ClinicPeopleView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ClinicPeople.objects.all()
    serializer_class = ClinicPeopleSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class ClinicTimingList(generics.ListCreateAPIView):
    queryset = ClinicTiming.objects.all().order_by('id')
    serializer_class = ClinicTimingSerializer

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def get_queryset(self):
        queryset = ClinicTiming.objects.all().order_by('id')
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class ClinicTimingView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ClinicTiming.objects.all()
    serializer_class = ClinicTimingSerializer

    def perform_update(self, serializer):
        # Set updated_by field
        serializer.save(updated_by=self.request.user)


class ClinicTimeAPI(APIView):
    permission_classes = []

    def post(self, request):
        queryset = ClinicTiming.objects.filter(
            id__in=[item.get('id', None) for item in request.data])
        serializer = ClinicTimingMultipleSerializer(queryset, data=request.data,
                                                    many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Timing was set successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)
