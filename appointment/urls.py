from django.urls import path, include

from .views import AppointmentView, AppointmentList, ProcedureView, \
    ProcedureList, FilesView, FilesList, ExerciseView, ExerciseList, \
    PatientDirectoryExercisesView, PatientDirectoryExercisesList, TaxView, \
    TaxList, CategoryView, CategoryList, AppointmentAll, \
    PatientDirectoryView, PatientDirectoryList, CreateAppointment, \
    CreateNotesView, NoteCategoryList, NoteCategoryView, UpComingsListView, \
    DoctorsAppointmentsListView, UpcomingAppointmentsView, \
    PatientCreateAppointment, BookedSlotsView, AppointmentsBookedByPatientsView, BookedDatesView, \
    AvailableDoctorsView, AppointmentPaymentStatus, AppointmentStatus

appointment_urls = [
    path('appointment/', include([
        path('', AppointmentList.as_view(),
             name='appointmentList'),
        path('all/', AppointmentAll.as_view(),
             name='appointmentList'),
        path('<int:pk>/', AppointmentView.as_view(),
             name='appointmentView'),
        path('create/', CreateAppointment.as_view()),
        path('patientdirectory/', PatientDirectoryList.as_view(),
             name='patientdirectoryList'),
        path('patientdirectory/<int:pk>/',
             PatientDirectoryView.as_view(),
             name='patientdirectoryView'),
        path('files/', FilesList.as_view(), name='filesList'),
        path('files/<int:pk>/', FilesView.as_view(), name='filesView'),

        path('patientdirectoryexercises/',
             PatientDirectoryExercisesList.as_view(),
             name='patientdirectoryexercisesList'),
        path('patientdirectoryexercises/<int:pk>/',
             PatientDirectoryExercisesView.as_view(),
             name='patientdirectoryexercisesView'),
        path('note/create/', CreateNotesView.as_view(),
             name='createnote'),
        path('doctors/count/',
             DoctorsAppointmentsListView.as_view(),
             name='DoctorsTodayAppointments'),
        path('upcoming-appointments/',
             UpcomingAppointmentsView.as_view(),
             name='upcoming-appointments'),  
        path('booked-dates/',
             BookedDatesView.as_view(),
             name='booked-dates'),         
        path('booked-slots/',
             BookedSlotsView.as_view(),
             name='booked-slots'),      
        path('booked-by-patients/',
             AppointmentsBookedByPatientsView.as_view(),
             name='booked-by-patients'),
        path('available-doctors/',
             AvailableDoctorsView.as_view(),
             name='available-doctors'),              
        path('patient/', include([
            path('create/', PatientCreateAppointment.as_view(), name='patient-create-appointment'),
        ])),
        path('payment/', include([
            path('status/<int:appointment_id>/', AppointmentPaymentStatus.as_view(), name='appointment-payment-status'),
        ])),
        path('status/<int:appointment_id>/', AppointmentStatus.as_view(), name='appointment-status'),  
    ])),

    path('exercise/', ExerciseList.as_view(), name='exerciseList'),
    path('exercise/<int:pk>/', ExerciseView.as_view(),
         name='exerciseView'),
    path('procedure/', ProcedureList.as_view(),
         name='procedureList'),
    path('procedure/<int:pk>/', ProcedureView.as_view(),
         name='procedureView'),
    path('tax/', TaxList.as_view(), name='taxList'),
    path('tax/<int:pk>/', TaxView.as_view(), name='taxView'),
    path('category/', CategoryList.as_view(), name='categoryList'),
    path('category/<int:pk>/', CategoryView.as_view(),
         name='categoryView'),
    path('notecategory/', NoteCategoryList.as_view(), name='categoryList'),
    path('notecategory/<int:pk>/', NoteCategoryView.as_view(),
         name='categoryView'),
    path('upcomings/', UpComingsListView.as_view(),
         name='UpComings'),
]
