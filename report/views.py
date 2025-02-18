import csv

from datetime import datetime
from django.db.models import Sum
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from base.utils import generate_pdf_file, custom_strftime
from clinic.models import Clinic
from appointment.models import Appointment
from appointment.serializers import AppointmentSerializer
from payment.models import Payment, Invoice, InvoiceItems
from payment.serializers import PaymentSerializer, InvoiceSerializer, InvoiceItemsSerializer
from report.utils import AppointmentReport


# Create your views here.


class AppointmentsReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.appointment_summary()
        return Response(summery, status=status.HTTP_200_OK)


class RevenueReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.revenue_summary()
        return Response(summery, status=status.HTTP_200_OK)


class BillingReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.billing_summary()
        return Response(summery, status=status.HTTP_200_OK)


class PaymentReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.payment_summary()
        return Response(summery, status=status.HTTP_200_OK)


class PaymentModeReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date')
        to_date = query.get('to_date')
        clinic_id = query.get('clinic_id', query.get('clinic'))

        if not from_date or not to_date or not clinic_id:
            return Response({'error': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
            summery = app.payment_mode_summary(request)
            return Response(summery, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EarningsPerProcedureReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.earnings_per_procedure(request)
        return Response(summery, status=status.HTTP_200_OK)


class AppointmentsPerDoctorReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.appointments_per_doctor(request)
        return Response(summery, status=status.HTTP_200_OK)


class InvoiceIncomePerDoctorReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.invoiced_income_per_doctor(request)
        return Response(summery, status=status.HTTP_200_OK)


class ReportBaseView(APIView):
    type_name = None
    csv_column_names = None
    template = None
    prefix_valus = {
        'payment_report_id': "RCPT",
        'payment_report_invoice_number': "INV",
        'income_report_invoice_number': "INV"
    }
    sufix_valus = {

    }

    def prefix_sufix(self, key, val):
        if not key or not val:
            return val
        key_name = self.type_name + '_' + key
        if key_name in self.prefix_valus.keys():
            val = self.prefix_valus[key_name] + str(val)
        if key_name in self.sufix_valus.keys():
            val = str(val) + self.sufix_valus[key_name]
        return val

    def export_csv(self, data):
        response = StreamingHttpResponse(
            content_type='text/csv',
            streaming_content=self.get_rows(data)
        )
        response['Content-Disposition'] = f'attachment; filename="{self.type_name}.csv"'
        return response

    def get_rows(self, data):
        writer = csv.writer(Echo())
        yield writer.writerow(self.csv_column_names.values())
        
        # Process in chunks
        chunk_size = 1000
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            for row in chunk:
                new_row = {k: v for k, v in row.items() if k in self.csv_column_names.keys()}
                yield writer.writerow([ 
                    self.prefix_sufix(column, new_row[column]) if column in new_row else '-' 
                    for column in self.csv_column_names.keys()
                ])

    def export_pdf(self, data):
        pdf_file = generate_pdf_file(f'pdf/{self.template}', data)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{self.type_name}.pdf"'

        return response
    
class Echo:
    def write(self, value):
        return value    

class IncomeReportExport(ReportBaseView):
    csv_column_names = {
        "sl_no": "Sl No.", "date": "Date", "invoice_number": "Invoice", "clinic_name": "Clinic", "doctor_name": "Doctor", "patient_name": "Patient",
        "patient_atlas_id": "Patient ID", "procedure_names": "Procedures", "cost": "Cost", "discount": "Discount",
        "tax": "Tax", "grand_total": "Invoice Amount", "paid_amount": "Paid Amount"
    }
    type_name = "income_report"
    template = "income.html"

    def format_date(self, date_string):
        if date_string:
            return datetime.strptime(date_string, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        user = request.user
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')
        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)
        clinic = get_object_or_404(Clinic, id=clinic_id)
        clinic_location = clinic.name
        today = custom_strftime('%d-%m-%Y')
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.income_summary()
        income = Invoice.objects.filter(clinic=clinic_id, date__range=(app.fdate, app.tdate))

        details = InvoiceSerializer(income, many=True).data

        details = sorted(details, key=lambda x: (x['date'], x['invoice_number']))

        for index, detail in enumerate(details, start=1):
            detail['sl_no'] = index
            
            invoice_obj = Invoice.objects.get(id=detail['id'])
            if hasattr(invoice_obj, 'appointment') and invoice_obj.appointment and invoice_obj.appointment.doctor:
                detail['doctor_name'] = invoice_obj.appointment.doctor.get_full_name()
            else:
                detail['doctor_name'] = '-'

        for detail in details:
            detail['date'] = self.format_date(detail['date'])

        data = {"user": user, "summery": summery, "details": details, "clinic_location": clinic_location,
                "from_date": app.fdate, "to_date": app.tdate, "today": today}

        if export_format == 'csv':
            return self.export_csv(details)
        elif export_format == 'pdf':
            return self.export_pdf(data)

class PaymentReportExport(ReportBaseView):
    csv_column_names = {
        "sl_no": "Sl No.", "collected_on": "Date", "receipt_id": "Receipt ID", "clinic_name": "Clinic", "doctor_name": "Doctor", "patient_name": "Patient",
        "patient_atlas_id": "Patient ID", "invoice_number": "Invoice", 'invoice_date': "Invoice Date",
        "procedure_names": "Procedures", "price": "Amount Paid (INR)", "advance_amount": "Advance Amount (INR)", "type": "Payment Type", "mode": "Payment Mode",
        "transaction_id": "Transaction ID", "payment_status": "Status", "advance": "Advance"
    }
    balance_keys = ["receipt_id", "collected_on", "clinic_name", "doctor_name", "patient_name", "patient_atlas_id",
                    "procedure_names", "price", "balance", "type", "mode", "transaction_id", "payment_status"]
    type_name = "payment_report"
    template = "payment.html"

    def format_date(self, date_string):
        if date_string:
            return datetime.strptime(date_string, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def balance_fix(self, row, total_balance):
        row['advance'] = "Yes"
        row['advance_amount'] = total_balance
        row['price'] = 0
        row['receipt_id'] = ''
        row['collected_on'] = ''
        row['doctor_name'] = '-'
        if total_balance > 0:
            row['invoice_number'] = ''
            row['invoice_date'] = ''
            row['procedure_names'] = ''
            row['type'] = ''
            row['mode'] = ''
            row['transaction_id'] = ''
            row['payment_status'] = ''
        return row

    def get_positive_balance_payments(self, patient_id, from_date, to_date):
        return Payment.objects.filter(
            patient=patient_id,
            balance__gt=0,
            collected_on__range=(from_date, to_date)
        )

    def aggregate_positive_balances(self, patient_id, from_date, to_date):
        positive_balance_payments = self.get_positive_balance_payments(patient_id, from_date, to_date)
        if positive_balance_payments.exists():
            total_balance = positive_balance_payments.aggregate(Sum('balance'))['balance__sum']
            if total_balance:
                base_record = PaymentSerializer(positive_balance_payments.first()).data
                return self.balance_fix(base_record, total_balance)
        return None

    def get(self, request):
        query = request.query_params
        user = request.user
        from_date = query.get('from_date')
        to_date = query.get('to_date')
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)

        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)

        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        clinic = get_object_or_404(Clinic, id=clinic_id)
        clinic_location = clinic.name
        today = custom_strftime('%d-%m-%Y')

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summery = app.payment_summary()

        payments = Payment.objects.filter(
            clinic=clinic_id,
            collected_on__range=(app.fdate, app.tdate),
            transaction_type__in=['collected', 'wallet_payment']
        ).order_by('collected_on', 'receipt_id', 'invoice__invoice_number')

        receipt_records = payments.distinct()
        details = PaymentSerializer(receipt_records, many=True).data

        unique_patient_ids = set(record['patient'] for record in details)

        aggregated_rows = {}
        for patient_id in unique_patient_ids:
            aggregated_row = self.aggregate_positive_balances(patient_id, app.fdate, app.tdate)
            if aggregated_row:
                aggregated_rows[patient_id] = aggregated_row

        for patient_id in unique_patient_ids:
            if patient_id in aggregated_rows:
                last_payment_index = max(index for index, detail in enumerate(details) if detail['patient'] == patient_id)
                details.insert(last_payment_index + 1, aggregated_rows[patient_id])

        for index, detail in enumerate(details, start=1):
            detail['sl_no'] = index

        for detail in details:
            detail['collected_on'] = self.format_date(detail['collected_on'])
            detail['invoice_date'] = self.format_date(detail['invoice_date'])

            payment_obj = Payment.objects.get(id=detail['id'])
            if (payment_obj.invoice and 
                payment_obj.invoice.appointment and 
                payment_obj.invoice.appointment.doctor):
                detail['doctor_name'] = payment_obj.invoice.appointment.doctor.get_full_name()
            else:
                detail['doctor_name'] = '-'

        data = {
            "user": user,
            "summery": summery,
            "details": details,
            "clinic_location": clinic_location,
            "from_date": app.fdate,
            "to_date": app.tdate,
            "today": today
        }

        if export_format == 'csv':
            return self.export_csv(details)
        elif export_format == 'pdf':
            return self.export_pdf(data)

class PaymentPerDayReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.payments_per_day(request)
        return Response(summery, status=status.HTTP_200_OK)

class IncomePerProcedureReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_income_per_procedure(request)
        return Response(summery, status=status.HTTP_200_OK)

class AppointmentPerProcedureReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_appointment_procedure(request)
        return Response(summery, status=status.HTTP_200_OK)
    
class AdvancePaymentsReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_advance_payments(request)
        
        return Response(summery, status=status.HTTP_200_OK)

class AppointmentReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_appointment(request)
        
        return Response(summery, status=status.HTTP_200_OK)

class CancelReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_cancellations(request)
        
        return Response(summery, status=status.HTTP_200_OK)

class DailyAppoitmentsReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_daily_appointments(request)
        
        return Response(summery, status=status.HTTP_200_OK)
    
class MonthlyAppoitmentsReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_monthly_appointments(request)
        
        return Response(summery, status=status.HTTP_200_OK)

class AppoitmentPlansReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_appointment_plans(request)
        
        return Response(summery, status=status.HTTP_200_OK)
    
class DailyPatientsReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_daily_patient(request)
        
        return Response(summery, status=status.HTTP_200_OK)
    
class MonthlyPatientsReportView(APIView):
    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        app = AppointmentReport(from_date=from_date, to_date=to_date,
                                clinic_id=clinic_id)
        summery = app.get_monthly_patient(request)
        
        return Response(summery, status=status.HTTP_200_OK)
    
def remove_rupee_symbol(value):
        # Strip ₹ and extra spaces if present
        return str(value).replace('₹', '').strip() if isinstance(value, str) else value

class PaymentModeReportExport(ReportBaseView):
    csv_column_names = {
        "type": "Type", "total": "Total"
    }
    type_name = "payment_report"
    template = "payment.html"

    def format_date(self, date_string):
        if date_string:
            return datetime.strptime(date_string, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')
        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)
        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.payment_mode_summary(request)

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            # Prepare data for CSV
            csv_data = [
                {
                    "type": remove_rupee_symbol(item.get("type", "")),
                    "total": remove_rupee_symbol(item.get("total", "")),
                }
                for item in results
            ]
            return self.export_csv(csv_data)

        return Response({
            'summary': summary_data
        }, status=status.HTTP_200_OK)

class IncomePerDoctorExport(ReportBaseView):
    csv_column_names = {
        "name": "Name",
        "cost": "Cost",
        "discounts": "Discounts",
        "income": "Income",
        "tax": "Tax",
        "invoice": "Invoice",
    }
    type_name = "income per doctor"
    template = "income_doctor.html"

    def format_date(self, collected_on):
        if collected_on:
            return datetime.strptime(collected_on, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.invoiced_income_per_doctor(request)

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            # Prepare data for CSV
            csv_data = [
                {
                    "name": remove_rupee_symbol(item.get("name", "")),
                    "cost": remove_rupee_symbol(item.get("cost", "")),
                    "discounts": remove_rupee_symbol(item.get("discounts", "")),
                    "income": remove_rupee_symbol(item.get("income", "")),
                    "tax": remove_rupee_symbol(item.get("tax", "")),
                    "invoice": remove_rupee_symbol(item.get("invoice", "")),
                }
                for item in results
            ]
            return self.export_csv(csv_data)

        return Response({
            'summary': summary_data
        }, status=status.HTTP_200_OK)

class AppointmentPerDoctorExport(ReportBaseView):
    csv_column_names = {
        "name":"Name","appointments": "Appointments", "cancelled": "Cancelled","attended":"Attended","no show":"No Show"
    }
    type_name = "appointment per doctor"
    template = "appointment_doctor.html"

    def format_date(self, scheduled_from):
        if scheduled_from:
            return datetime.strptime(scheduled_from, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.appointments_per_doctor(request)

        income = Appointment.objects.filter(invoice__clinic=clinic_id, scheduled_from__range=(app.fdate, app.tdate))
        details = AppointmentSerializer(income, many=True).data
        details = sorted(details, key=lambda x: (x['scheduled_from']))

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            summary_row = [
                {
                    "total": item.get("total", ""),
                    "name": item.get("name", ""), 
                    "appointments": item.get("appointments", ""), 
                    "cancelled": item.get("cancelled", ""), 
                    "attended": item.get("attended", ""), 
                    "no show": item.get("no_show", "")
                    } 
                    for item in results
                ]
            return self.export_csv(summary_row)

        return Response({
            'summary': results
        }, status=status.HTTP_200_OK)

class PaymentsPerDayExport(ReportBaseView):
    csv_column_names = {
        "date": "Date", "upi": "Upi", "card": "Card", "cash": "Cash", "net banking": "Net Banking", "total": "Total"
    }
    type_name = "payment per day"
    template = "payment_day.html"

    def format_date(self, collected_on):
        if collected_on:
            return datetime.strptime(collected_on, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.payments_per_day(request)

        income = Payment.objects.filter(clinic=clinic_id, collected_on__range=(app.fdate, app.tdate))
        details = PaymentSerializer(income, many=True).data
        details = sorted(details, key=lambda x: (x['collected_on'], x['invoice_number']))

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            summary_row = [{"date": item.get("date", ""), 
                            "upi": remove_rupee_symbol(item.get("upi", "")), 
                            "card": remove_rupee_symbol(item.get("card", "")), 
                            "cash": remove_rupee_symbol(item.get("cash", "")), 
                            "net banking": remove_rupee_symbol(item.get("net_banking", "")), 
                            "total": remove_rupee_symbol(item.get("total", ""))} for item in results]
            return self.export_csv(summary_row)

        return Response({
            'summary': results
        }, status=status.HTTP_200_OK)

class IncomePerProcedureExport(ReportBaseView):
    csv_column_names = {
        "s.no.": "S.no.", "procedure": "Procedure","cost":"Cost","discount":"Discount","income":"Income"
    }
    type_name = "income per procedure"
    template = "income_procedure.html"

    def format_date(self, invoice__date):
        if invoice__date:
            return datetime.strptime(invoice__date, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.get_income_per_procedure(request)

        income = InvoiceItems.objects.filter(invoice__clinic=clinic_id, invoice__date__range=(app.fdate, app.tdate))
        details = InvoiceItemsSerializer(income, many=True).data
        #details = sorted(details, key=lambda x: (x['invoice__date'], x['invoice__id']))

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            summary_row = [{"s.no.": item.get("s.no.", ""), 
                            "procedure": item.get("procedure", ""), 
                            "cost": remove_rupee_symbol(item.get("cost", "")), 
                            "discount": remove_rupee_symbol(item.get("discount", "")), 
                            "income": remove_rupee_symbol(item.get("income", ""))} for item in results]
            return self.export_csv(summary_row)

        return Response({
            'summary': results
        }, status=status.HTTP_200_OK)

class AppointmentPerProcedureExport(ReportBaseView):
    csv_column_names = {
        "s.no.": "S.no.", "procedure": "Procedure","count":"Count"
    }
    type_name = "appointment per procedure"
    template = "appointment_procedure.html"

    def format_date(self, scheduled_from):
        if scheduled_from:
            return datetime.strptime(scheduled_from, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.get_appointment_procedure(request)

        income = Appointment.objects.filter(clinic=clinic_id, scheduled_from__range=(app.fdate, app.tdate))
        details = AppointmentSerializer(income, many=True).data
        details = sorted(details, key=lambda x: (x['scheduled_from']))

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            summary_row = [{"s.no.": item.get("s.no.", ""), 
                            "procedure": item.get("procedure", ""), 
                            "count": item.get("count", "")} for item in results]
            return self.export_csv(summary_row)

        return Response({
            'summary': results
        }, status=status.HTTP_200_OK)

class AdvancePaymentExport(ReportBaseView):
    csv_column_names = {
        "s.no.": "S.no.","name": "Name", "id": "Id","received":"Received","deducted":"Deducted","balance":"Balance","due":"Due"
    }
    type_name = "advance payment"
    template = "advance_payment.html"

    def format_date(self, collected_on):
        if collected_on:
            return datetime.strptime(collected_on, '%Y-%m-%d').strftime('%d-%m-%Y')
        return ''

    def get(self, request):
        query = request.query_params
        from_date = query.get('from_date', None)
        to_date = query.get('to_date', None)
        clinic_id = query.get('clinic_id', query.get('clinic'))
        export_format = query.get('filetype', 'csv')

        if export_format not in ['csv', 'pdf']:
            return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)
        if not from_date or not to_date:
            return Response({'error': 'Invalid date range'}, status=status.HTTP_400_BAD_REQUEST)
        if not clinic_id:
            return Response({'error': 'Invalid clinic ID'}, status=status.HTTP_400_BAD_REQUEST)

        app = AppointmentReport(from_date=from_date, to_date=to_date, clinic_id=clinic_id)
        summary_data = app.get_advance_payments(request)

        income = Payment.objects.filter(clinic=clinic_id, collected_on__range=(app.fdate, app.tdate))
        details = PaymentSerializer(income, many=True).data
        details = sorted(details, key=lambda x: (x['collected_on']))

        if not isinstance(summary_data, dict) or "results" not in summary_data:
            return Response(
                {'error': 'Invalid data format from invoiced_income_per_doctor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = summary_data["results"]

        if export_format == 'csv':
            summary_row = [{"s.no.": item.get("s.no.", ""),
                            "name": item.get("name", ""),
                            "id": item.get("Id", ""), 
                            "received": remove_rupee_symbol(item.get("received", "")),
                            "deducted": remove_rupee_symbol(item.get("deducted", "")),
                            "balance": remove_rupee_symbol(item.get("Balance", "")),
                            "due": remove_rupee_symbol(item.get("due", ""))} for item in results]
            return self.export_csv(summary_row)

        return Response({
            'summary': results
        }, status=status.HTTP_200_OK)