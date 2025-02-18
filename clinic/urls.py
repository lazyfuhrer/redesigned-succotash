from django.urls import path, include

from .views import ClinicView, ClinicList, ClinicPeopleView, ClinicPeopleList, \
    ClinicTimingList, ClinicTimingView, ClinicTimeAPI

clinic = [
    path('', ClinicList.as_view(), name='ClinicList'),
    path('<int:pk>/', ClinicView.as_view(), name='ClinicView'),
    path('people/', ClinicPeopleList.as_view(), name='ClinicPeopleList'),
    path('people/<int:pk>/', ClinicPeopleView.as_view(),
         name='ClinicPeopleView'),
    path('timing/', ClinicTimingList.as_view(), name='ClinicTimingList'),
    path('timing/<int:pk>/', ClinicTimingView.as_view(),
         name='ClinicTimingView'),
    path('timings/', ClinicTimeAPI.as_view()),
]
clinic_urls = [
    path('clinic/', include(clinic)),

]
