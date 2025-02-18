from django.urls import path, include

from .views import AppointmentsReportView, RevenueReportView, BillingReportView, \
    PaymentReportView, PaymentModeReportView, IncomeReportExport, PaymentReportExport, \
        EarningsPerProcedureReportView, AppointmentsPerDoctorReportView, \
          InvoiceIncomePerDoctorReportView, PaymentPerDayReportView, IncomePerProcedureReportView, \
               AppointmentPerProcedureReportView, AdvancePaymentsReportView, AppointmentReportView, \
               CancelReportView, DailyAppoitmentsReportView, MonthlyAppoitmentsReportView, \
               AppoitmentPlansReportView, DailyPatientsReportView, MonthlyPatientsReportView, \
                    PaymentModeReportExport, IncomePerDoctorExport, AppointmentPerDoctorExport, \
                    PaymentsPerDayExport, IncomePerProcedureExport, AppointmentPerProcedureExport, \
                         AdvancePaymentExport

report_urls = [
    path('report/', include([
        path('export/', include([
            path('income/', IncomeReportExport.as_view(), name="income_export"),
            path('payment/', PaymentReportExport.as_view(), name="payment_export"),
            path('payment-mode/', PaymentModeReportExport.as_view(),
                         name="paymentmode_export"),
            path('payment-day/', PaymentsPerDayExport.as_view(),
                         name="paymentday_export"),
            path('income-doctor/', IncomePerDoctorExport.as_view(),
                         name="incomedoctor_export"),
            path('income-procedure/', IncomePerProcedureExport.as_view(),
                         name="incomeprocedure_export"),             
            path('appointment-doctor/', AppointmentPerDoctorExport.as_view(),
                         name="appointmentdoctor_export"),
            path('appointment-procedure/', AppointmentPerProcedureExport.as_view(),
                         name="appointmentprocedure_export"),
            path('advance-payment/', AdvancePaymentExport.as_view(),
                         name="advancepayment_export"),
            path('appointments-export/', AppointmentPerProcedureExport.as_view(),
                         name="appointments_export"),
        ])),
        path('summery/', include([
            path('appointment/', AppointmentsReportView.as_view(),
                 name="appintment_summery"),
            path('revenue/', RevenueReportView.as_view(),
                 name="revenue_summery"),
            path('billing/', BillingReportView.as_view(),
                 name="billing_summery"),
            path('procedure/', EarningsPerProcedureReportView.as_view(),
                 name="procedure"),
            path('appointmentsperdoctor/', AppointmentsPerDoctorReportView.as_view(),
                 name="appointment_per_doctor"),
            path('invoicedincome/', InvoiceIncomePerDoctorReportView.as_view(),
                 name="invoicedincome"),
            path('payment-report/', PaymentPerDayReportView.as_view(), name='payment-report'),
            path('incomeperprocedure/', IncomePerProcedureReportView.as_view(), name='incomeperprocedure'),
            path('appointmentperprocedure/', AppointmentPerProcedureReportView.as_view(), name='appointmentperprocedure'),
            path('advance_payments/', AdvancePaymentsReportView.as_view(), name='advance_payments'),
            path('appointments/', AppointmentReportView.as_view(),
                 name="appointments"),
            path('cancel/', CancelReportView.as_view(),
                 name="cancel"),
            path('daily-appointments/', DailyAppoitmentsReportView.as_view(),
                 name="daily-appointments"),
            path('monthly-appointments/', MonthlyAppoitmentsReportView.as_view(),
                 name="monthly-appointments"),
            path('plans/', AppoitmentPlansReportView.as_view(),
                 name="plans"),
            path('daily-patients/', DailyPatientsReportView.as_view(),
                 name="daily-paitents"),
            path('monthly-patients/', MonthlyPatientsReportView.as_view(),
                 name="monthly-paitents"),
            path('payment/', include([
                path('mode/', PaymentModeReportView.as_view(),
                     name="paymentmode_summery"),
                path('', PaymentReportView.as_view(),
                     name="payment_summery"),
            ]))
        ])),

    ]))
]
