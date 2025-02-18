import csv, json, hmac, hashlib
import logging, traceback
from itertools import chain
import requests

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import generics, filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from appointment.models import Appointment, Procedure
from appointment.serializers import AppointmentSerializer
from base.utils import generate_pdf_file, send_attachment_email, patient_booking_notifications
from .models import Invoice, InvoiceItems, Payment, Refund, User
from .serializers import InvoiceSerializer, InvoiceItemsSerializer, \
    PaymentSerializer, BillingSerializer, InvoiceAllSerializer, RefundSerializer
from .utils import get_user_wallet_balance, add_user_wallet_balance, \
    get_user_advance_balance, PHONEPE_BASE_URL, generate_phonepe_payload, \
    generate_x_verify_header, get_headers, MERCHANT_ID, \
    generate_random_string, base64_to_json, create_invoice_and_payment

from clinic.models import Clinic
from appointment.models import AppointmentState

import razorpay

from .utils import RAZORPAY_CLIENT_ID, RAZORPAY_CLIENT_SECRET

logger = logging.getLogger('fuelapp')


class InvoiceList(generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    filter_backends = [filters.SearchFilter]
    serializer_class = InvoiceSerializer
    search_fields = ['invoice_number', 'patient__first_name',]

    def get_queryset(self):
        queryset = Invoice.objects.all().order_by('-id')
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class InvoiceAll(viewsets.ViewSet):
    queryset = Invoice.objects.all()
    filter_backends = [filters.SearchFilter]
    serializer_class = InvoiceAllSerializer
    search_fields = ['invoice_number', 'appointment__patient__first_name',
                     'appointment__patient__last_name',
                     'appointment__patient__email']
    pagination_class = None

    def get_queryset(self):
        queryset = Invoice.objects.all().order_by('-id')
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})

        return queryset

    @action(detail=False, methods=['get'])
    def list(self, request):
        mixed_results = self.get_queryset()
        serializer = InvoiceAllSerializer(mixed_results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def download_invoice_report(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="invoice_report.csv"'

        invoices = self.get_queryset()

        writer = csv.writer(response)
        writer.writerow(
            ['Invoice Number', 'Patient First Name', 'Patient Last Name', 'Patient Email', 'Patient Phone Number',
             'Grand Total'])

        for invoice in invoices:
            writer.writerow([invoice.invoice_number, invoice.patient.first_name,
                             invoice.patient.last_name, invoice.patient.email, invoice.patient.phone_number,
                             invoice.grand_total])

        return response


class InvoiceView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        appointment = instance.appointment
        appointment.payment_status = 'pending'
        appointment.save()
        return self.destroy(request, *args, **kwargs)


class InvoiceItemsList(generics.ListCreateAPIView):
    queryset = InvoiceItems.objects.all()
    serializer_class = InvoiceItemsSerializer

    def get_queryset(self):
        queryset = InvoiceItems.objects.all()
        params = self.request.query_params
        if params and len(params) > 0:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset


class InvoiceItemsView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InvoiceItems.objects.all()
    serializer_class = InvoiceItemsSerializer


class PaymentList(generics.ListCreateAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['invoice__appointment__patient__first_name',
                     'invoice__appointment__patient__last_name',
                     'invoice__appointment__patient__email',
                     'invoice__invoice_number']

    def get_queryset(self):
        queryset = Payment.objects.all().order_by('-id')
        params = self.request.query_params
        fields = [field.name for field in Payment._meta.fields]
        if params and len(params) > 0:
            for param in params:
                if param.split('__')[0] in fields:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset

    def perform_create(self, serializer):
        # Set created_by and updated_by fields
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)


class PaymentView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer


class CollectPayment(APIView):
    def patch(self, request, pk, format=None):
        with transaction.atomic():
            data = request.data
            items = data.pop('items')
            payments = data.pop('payment')
            userid = self.request.user.id
            grand_total = data.get('grand_total')
            appointment_id = data.get('appointment')
            data.update({'updated_by': userid})
            invoice = Invoice.objects.get(id=pk)
            invoice_serializer = InvoiceSerializer(invoice, data=data)
            prev_items = InvoiceItems.objects.filter(invoice=invoice.id)
            valid_items = []
            if invoice_serializer.is_valid():
                invoice_serializer.save()
                for item in items:
                    item['updated_by'] = userid
                    item_id = item['id']
                    prev_item = InvoiceItems.objects.get(id=item_id)
                    valid_items.append(item_id)
                    inv_items_serializer = InvoiceItemsSerializer(prev_item,
                                                                  data=item,
                                                                  partial=True)
                    if inv_items_serializer.is_valid():
                        inv_items_serializer.save()
                    else:
                        logger.error(f"update_payment pk {item_id} ->"
                                     f" {inv_items_serializer.errors} - "
                                     f"invoice items failed")
                        return Response(inv_items_serializer.errors,
                                        status=status.HTTP_400_BAD_REQUEST)
                # delete items that are not present in the request
                prev_items.exclude(id__in=valid_items).delete()
                payment_sum = 0
                for payment in payments:
                    payment['updated_by'] = userid
                    pay_id = payment['id']
                    pay = Payment.objects.get(id=pay_id)

                    g_total = Invoice.objects.get(id=payment["invoice"]).grand_total
                    new_excess = float(payment["price"]) - g_total

                    if new_excess > payment["balance"]:
                        new_bal = new_excess - payment["balance"]
                        payment["excess_amount"] = new_excess
                        payment["balance"] += new_bal
                    elif new_excess < payment["balance"]:
                        new_bal = payment["balance"] - new_excess
                        payment["excess_amount"] = new_excess
                        payment["balance"] -= new_bal

                    payment_serializer = PaymentSerializer(pay, data=payment, partial=True)
                    if payment_serializer.is_valid():
                        payment_serializer.save()
                        payment_sum += payment_serializer.data['price']
                    else:
                        logger.error(f"update_payment pk {pay_id} ->"
                                     f" {payment_serializer.errors} - "
                                     f"payment failed")
                if grand_total >= payment_sum:
                    appointment = Appointment.objects.get(id=appointment_id)
                    appointment.payment_status = 'collected'
                    appointment.save()
                return Response(invoice_serializer.data,
                                status=status.HTTP_202_ACCEPTED)
            else:
                logger.error(f"update_payment"
                             f" {invoice_serializer.errors} - "
                             f"invoice failed")
                return Response(invoice_serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        data = request.data
        userid = self.request.user.id
        partial = data.pop('partial', False)
        data.update({'created_by': userid,
                     'updated_by': userid})
        items = data.pop('items')
        payment = {}
        transaction_id = data.pop('payment_transaction_id')
        payment_status = data.pop('payment_status')
        payment_type = data.pop('payment_type')
        payment_mode = data.pop('payment_mode')
        amount = float(data.pop('amount', 0) or 0)
        date = data.get('date')
        notes = data.get('notes')
        wallet_deduct = data.pop('wallet_deduct')
        wallet_balance = float(data.pop('wallet_balance'))
        
        # Check if appointment is present in the request data
        if 'appointment' in data:
            appid = data['appointment']
            appointment = Appointment.objects.get(id=appid)
            patient = appointment.patient
            clinic = appointment.clinic
        else:
            # Extract patient and clinic from the request data
            patient_id = data.pop('patient')
            clinic_id = data.pop('clinic')
            patient = User.objects.get(id=patient_id)
            clinic = Clinic.objects.get(id=clinic_id)

        data.update({'patient': patient.id, 'clinic': clinic.id})    

        # InvoiceSerializer
        invoice_serializer = InvoiceSerializer(data=data)
        if invoice_serializer.is_valid():
            invoice_serializer.save()
            invoice = invoice_serializer.data
            invoice_id = invoice['id']

            # InvoiceItemsSerializer
            for item in items:
                item['created_by'] = userid
                item['updated_by'] = userid
                item['invoice'] = invoice_id

            inv_items_serializer = InvoiceItemsSerializer(data=items,
                                                          many=True)
            grand_total = float(invoice['grand_total'])
            balance = (amount + wallet_balance) - grand_total if wallet_deduct else amount - grand_total
            if inv_items_serializer.is_valid():
                inv_items_serializer.save()
                if amount > 0:
                    payment.update({
                        'patient': patient.id,
                        'clinic': clinic.id,
                        'transaction_id': transaction_id,
                        'price': amount,
                        'payment_status': payment_status,
                        'invoice': invoice_id,
                        'balance': amount if balance > amount else balance,
                        'excess_amount': amount if balance > amount else balance,
                        'type': payment_type,
                        'mode': payment_mode,
                        'created_by': userid,
                        'collected_on': date,
                        'pay_notes': notes,
                        'updated_by': userid})
                    # PaymentSerializer
                    payment_serializer = PaymentSerializer(data=payment)
                    if payment_serializer.is_valid():
                        payment_serializer.save()
                        Payment.objects.filter(id=payment_serializer.data.get('id')).update(
                            receipt_id=payment_serializer.data.get('id')
                        )
                    else:
                        logger.error(f"collect_payment"
                                     f" {payment_serializer.errors} - "
                                     f"payment failed")
                        return Response(payment_serializer.errors,
                                        status=status.HTTP_400_BAD_REQUEST)

                    # if balance is there add to wallet

                    # patient_id = appointment.patient.id

                if wallet_deduct:
                    # balance = wallet_balance - balance
                    invoice_balance = grand_total - wallet_balance
                    wallet_amount = wallet_balance if invoice_balance >= 0 else grand_total
                    if wallet_amount:
                        wallet_pay = {
                            'invoice': invoice_id,
                            'clinic': clinic.id,
                            'patient': patient.id,
                            'type': 'wallet',
                            'mode': 'offline',
                            'price': wallet_amount,
                            'transaction_id': 'wallet_payment',
                            'excess_amount': -abs(wallet_amount),
                            'transaction_type': 'wallet_payment',
                            'payment_status': 'success',
                            'collected_on': date,
                            'pay_notes': 'Wallet deducted for payment',
                            'created_by': userid,
                            'updated_by': userid
                        }
                        add_user_wallet_balance(wallet_amount, wallet_pay, patient.id)
                        # wallet_pay_serializer = PaymentSerializer(data=wallet_pay)
                        # if wallet_pay_serializer.is_valid():
                        #     wallet_pay_serializer.save()
                        # else:
                        #     logger.error(f"collect_payment"
                        #                  f" {wallet_pay_serializer.errors} - "
                        #                  f"payment failed")
                        #     return Response(wallet_pay_serializer.errors,
                        #                     status=status.HTTP_400_BAD_REQUEST)

                if 'appointment' in data:
                    appointment.payment_status = 'partial_paid' if balance < 0 else 'collected'
                    appointment.save()
                Invoice.objects.filter(id=invoice_id).update(is_paid=False if balance < 0 else True)
                return Response(invoice_serializer.data,
                                status=status.HTTP_201_CREATED)
            else:
                logger.error(f"collect_payment"
                             f" {inv_items_serializer.errors} - "
                             f"invoice items failed")
                return Response(inv_items_serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)
        logger.error(f"collect_payment"
                     f" {invoice_serializer.errors} - "
                     f"invoice failed")
        return Response(invoice_serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class CollectDuePayment(APIView):
    def patch(self, request, pk, format=None):
        return Response(status=status.HTTTP_405_METHOD_NOT_ALLOWED)

    def post(self, request):
        data = request.data
        userid = self.request.user.id
        data.update({'created_by': userid,
                     'updated_by': userid})
        payment = {}
        transaction_id = data.pop('payment_transaction_id')
        payment_status = data.pop('payment_status')
        payment_type = data.pop('payment_type')
        payment_mode = data.pop('payment_mode')
        amount = float(data.pop('amount', 0) or 0)
        invoice_id = data.pop('invoice')
        date = data.get('date')
        notes = data.get('notes')
        wallet_deduct = data.pop('wallet_deduct')
        wallet_balance = data.pop('wallet_balance')

        invoice = Invoice.objects.get(id=invoice_id)
        invoice_serializer = InvoiceSerializer(invoice)
        invoice_data = invoice_serializer.data
        appointment = Appointment.objects.get(id=invoice_data['appointment'])
        patient = appointment.patient
        clinic = appointment.clinic
        due = invoice_data['due_amount']
        balance = amount - due
        # balance = balance if balance > 0 else 0
        if due > 0:
            if amount > 0:
                payment.update({
                    'transaction_id': transaction_id,
                    'price': amount,
                    'payment_status': payment_status,
                    'invoice': invoice_id,
                    'clinic': clinic.id,
                    'collected_on': date,
                    'type': payment_type,
                    'balance': balance if balance > 0 else 0,
                    'excess_amount': balance if balance > 0 else 0,
                    'mode': payment_mode,
                    'pay_notes': notes,
                    'created_by': userid,
                    'updated_by': userid,
                    'patient': patient.id
                })
                payment_serializer = PaymentSerializer(data=payment)
                if payment_serializer.is_valid():
                    payment_serializer.save()
                    Payment.objects.filter(id=payment_serializer.data.get('id')).update(
                        receipt_id=payment_serializer.data.get('id')
                    )

                else:
                    return Response(payment_serializer.errors,
                                    status=status.HTTP_400_BAD_REQUEST)

            if wallet_deduct:
                balance = wallet_balance - balance
                total_deduct = due - wallet_balance
                wallet_amount = wallet_balance if total_deduct >= 0 else due
                if wallet_amount:
                    wallet_pay = {
                        'invoice': invoice_id,
                        'clinic': clinic.id,
                        'patient': patient.id,
                        'type': 'wallet',
                        'mode': 'offline',
                        'price': wallet_amount,
                        'transaction_id': 'wallet_payment',
                        'excess_amount': -abs(wallet_amount),
                        'transaction_type': 'wallet_payment',
                        'payment_status': 'success',
                        'collected_on': date,
                        'pay_notes': 'Wallet deducted for payment',
                        'created_by': userid,
                        'updated_by': userid
                    }

                    # wallet_pay_serializer = PaymentSerializer(data=wallet_pay)
                    # if wallet_pay_serializer.is_valid():
                    #     wallet_pay_serializer.save()
                    # else:
                    #     logger.error(f"collect_payment"
                    #                  f" {wallet_pay_serializer.errors} - "
                    #                  f"payment failed")
                    #     return Response(wallet_pay_serializer.errors,
                    #                     status=status.HTTP_400_BAD_REQUEST)
                    # add_user_wallet_balance(
                    #     wallet_amount,
                    #     patient.id,
                    #     invoice_id,
                    #     userid,
                    #     'deduct balance from wallet for due payment'
                    # )

                    add_user_wallet_balance(wallet_amount, wallet_pay, patient.id)
                # balance = float(amount) - due
                # if balance != 0:
                #     patient_id = invoice_data['patient']
                #     # get user from appoint ment
                #     add_user_wallet_balance(balance, patient_id,
                #                             invoice_id, userid)
            try:
                appointment.payment_status = 'partial_paid' if balance < 0 else 'collected'
                appointment.save()
                Invoice.objects.filter(id=invoice_id).update(is_paid=False if balance < 0 else True)
            except Exception as e:
                logger.error(f"error on update payment status - {e}")
                return Response({'message': 'failed to update appointment status after due payment'},
                                status=status.HTTP_417_EXPECTATION_FAILED)
            return Response(invoice_serializer.data,
                            status=status.HTTP_201_CREATED)

        else:
            return Response({'message': 'No due amount'}, status=204)


# class WalletList(generics.ListCreateAPIView):
#     queryset = Wallet.objects.all()
#     serializer_class = WalletSerializer
#
#     def get_queryset(self):
#         queryset = Wallet.objects.all()
#         params = self.request.query_params
#         if params and len(params) > 0:
#             for param in params:
#                 if param not in ['page', 'search']:
#                     queryset = queryset.filter(**{param: params[param]})
#         return queryset


class WalletBalanceView(APIView):
    def get(self, request, user_id):
        # Get sum of debit and credit for the authenticated user
        final_balance = get_user_wallet_balance(user_id)

        return JsonResponse(
            {'user_id': request.user.id, 'final_balance': final_balance})


class AdvanceBalanceView(APIView):
    def get(self, request, user_id):
        # Get sum of debit and credit for the authenticated user
        exclude_invoice = request.query_params.get('invoice__exclude', None)
        final_balance = get_user_advance_balance(user_id, exclude_invoice)

        return JsonResponse(
            {'user_id': request.user.id, 'final_balance': final_balance})


# class WalletView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Wallet.objects.all()
#     serializer_class = WalletSerializer


class GenerateInvoicePDFView(APIView):
    def get(self, request, pk):
        invoice = Invoice.objects.get(id=pk)
        context = {}
        invoice_data = InvoiceSerializer(invoice).data
        final_balance = get_user_wallet_balance(invoice_data['patient_id'])
        template_name = 'pdf/invoice.html'
        # Generate the PDF
        appointment = Appointment.objects.get(
            id=invoice_data['appointment']
        )
        appointment_data = AppointmentSerializer(appointment).data
        context.update({
            'invoice': invoice_data,
            'wallet_balance': final_balance,
            'appointment': appointment_data,
        })
        pdf_file = generate_pdf_file(template_name, context)

        # Create an HTTP response with the PDF attachment
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="invoice.pdf"'

        return response


class SendInvoiceEmailView(APIView):
    def get(self, request, pk):
        invoice = Invoice.objects.get(id=pk)
        invoice_data = InvoiceSerializer(invoice)
        template_name = 'email/invoice.html'
        pdf_template = 'invoice.html'
        to_email = invoice_data.data['patient_email']
        subject = f'Atlas - Invoice #{invoice_data.data["invoice_number"]}'

        # Send the invoice email
        send_attachment_email(template_name, pdf_template, invoice_data.data,
                              to_email,
                              subject)
        return Response(status=status.HTTTP_200_OK)


class BillingView(viewsets.ViewSet):

    def list(self, request):
        mixed_results = self.get_queryset()
        serializer = BillingSerializer(mixed_results, many=True)
        return Response(serializer.data)

    def get_queryset(self):

        invoice_results = Invoice.objects.all()
        invoice_fields = [field.name for field in Invoice._meta.get_fields()]

        payment_results = Payment.objects.all().exclude(
            invoice__isnull=False)
        payment_fields = [field.name for field in Payment._meta.get_fields()]

        params = self.request.query_params
        remove_all = ['page', 'search']
        if params and len(params) > 0:
            for param in params:
                if param in invoice_fields or param.split('__')[0] in invoice_fields and param not in remove_all:
                    invoice_results = invoice_results.filter(**{param: params[param]})

                if param in payment_fields or param.split('__')[0] in payment_fields and param not in remove_all:
                    payment_results = payment_results.filter(**{param: params[param]})

        for payment in payment_results:
            payment.sorting_date = payment.collected_on

        for invoice in invoice_results:
            invoice.sorting_date = invoice.date

        result_list = sorted(chain(payment_results, invoice_results), key=lambda data: data.sorting_date, reverse=True)

        return result_list

# class BillingView(APIView):
#     def get(self, request):
#         # Number of items per page
#         items_per_page = 10
#
#         # Get the mixed results queryset
#         mixed_results = (Invoice.objects.all()
#                          | Payment.objects.exclude(invoice__isnull=False))
#
#         # Apply pagination
#         paginator = PageNumberPagination()
#         paginator.page_size = items_per_page
#         mixed_results_page = paginator.paginate_queryset(mixed_results, request)
#
#         # Serialize the queryset
#         serializer = MixedResultsSerializer(mixed_results_page, many=True)
#
#         return paginator.get_paginated_response(serializer.data)

def process_payment(patient_data, amount=1):
    base64_request, finalXHeader = generate_phonepe_payload(patient_data, amount)
    # payment_url = f"{PHONEPE_BASE_URL}/pay"
    payment_url = f"{PHONEPE_BASE_URL}/pg/v1/pay"
    req = {"request": base64_request}
    headers = get_headers(finalXHeader)
    response = requests.post(payment_url, headers=headers, json=req)
    return response

def process_razorpay_payment(patient_data, amount=500):
    try:
        client = razorpay.Client(auth=(RAZORPAY_CLIENT_ID, RAZORPAY_CLIENT_SECRET))

        payment_link_data = {
            "amount": amount * 100,
            "currency": "INR",
            "description": "Advance Payment",
            "customer": {
                "name": patient_data["full_name"],
                "email": patient_data["email"],
                "contact": patient_data["phone_number"]
            },
            "notify": {
                "sms": True,
                "email": True
            },
            "reminder_enable": True,
            "callback_url": f"{settings.FRONTEND_URL}patients/thankyou",
            "callback_method": "get"
        }

        payment_link = client.payment_link.create(payment_link_data)
        return payment_link
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Error creating payment link: {e}")
        return None

# class PaymentStatusView(APIView):
#     permission_classes = []

#     def post(self, request):
#         merchant_id = MERCHANT_ID
#         encoded_tx_id = request.data.get('transaction_id')
#         if not encoded_tx_id:
#             return Response({
#                 'state': False,
#                 'data': {
#                     'Error': ['transaction_id is required']
#                 }
#             }, status=status.HTTP_400_BAD_REQUEST)

#         appointment_transaction_id = encoded_tx_id
#         merchant_transaction_id = encoded_tx_id

#         input_string = f"/pg/v1/status/{merchant_id}/{merchant_transaction_id}"
#         finalXHeader = generate_x_verify_header(input_string)
#         status_url = f"{PHONEPE_BASE_URL}/pg/v1/status/{merchant_id}/{merchant_transaction_id}"
#         headers = get_headers(finalXHeader)

#         appointment_data = cache.get(appointment_transaction_id)
#         if appointment_data is None:
#             return Response({
#                 'state': False,
#                 'data': {
#                     'CacheError': ['Data not found inside cache']
#                 }
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         clinic = Clinic.objects.get(id=appointment_data['clinic'])

#         try:
#             response = requests.get(status_url, headers=headers)
#             response.raise_for_status()
#             response_data = response.json()
#             code = response_data.get('code')

#             if not response_data.get('success'):
#                 return Response({
#                     'state': False,
#                     'code': code,
#                     'data': {
#                         'Error': [response_data["message"]]
#                     }
#                 }, status=response.status_code)

#             if code == 'PAYMENT_SUCCESS':

#                 try:
#                     pending_appointment = AppointmentState.objects.get(
#                         appointment=appointment_data['appointment']
#                     )
#                     pending_appointment.payment_status = 'completed'
#                     pending_appointment.save()

#                     # Update the appointment status to 'booked'
#                     appointment = pending_appointment.appointment
#                     appointment.appointment_status = 'booked'
#                     appointment.save()

#                     pending_appointment.convert_to_appointment()

#                 except AppointmentState.DoesNotExist:
#                     logger.error(f"PendingAppointment not found for appointment {appointment_data['appointment'].id}")

#                 amount = round(response_data["data"]["amount"] / 100)
#                 procedure = Procedure.objects.filter(clinic_id=appointment_data['clinic'], name='Advance Amount').first()

#                 payment_instrument_type = response_data["data"].get("paymentInstrument", {}).get("type", "").upper()
#                 payment_type = "cash"

#                 if payment_instrument_type == "NETBANKING":
#                     payment_type = "netbanking"
#                 elif payment_instrument_type == "UPI":
#                     payment_type = "upi"
#                 elif payment_instrument_type == "CARD":
#                     payment_type = "card"

#                 # Check if Invoice already exists
#                 invoice = Invoice.objects.filter(
#                     appointment=appointment_data['appointment'],
#                     invoice_number=appointment_data['appointment'].id,
#                     clinic_id=appointment_data['clinic']
#                 ).first()

#                 if not invoice:
#                     if not create_invoice_and_payment(appointment_data, amount, procedure, payment_type):
#                         return Response({
#                             'state': False,
#                             'data': {
#                                 'Error': ['Error during atomic transaction']
#                             }
#                         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#                 patient_booking_notifications(appointment_data)

#                 cache.delete(appointment_transaction_id)

#                 clinic_details = {
#                     'clinic_name': clinic.name,
#                     'clinic_location': clinic.map_link,
#                     'clinic_contact_number': f"+91 {str(clinic.phone_no_1)[-10:]}"
#                 }

#                 return Response({
#                     'state': True,
#                     'message': 'Appointment created successfully',
#                     'data': clinic_details
#                 }, status=status.HTTP_201_CREATED)

#         except Exception as e:
#             logger.error(f"Unexpected error: {e}")
#             logger.error(traceback.format_exc())
#             return Response({
#                 'state': False,
#                 'data': {
#                     'Error': [str(e)]
#                 }
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentStatusView(APIView):
    permission_classes = []

    def post(self, request):
        encoded_tx_id = request.data.get('razorpay_payment_link_id')
        if not encoded_tx_id:
            return Response({
                'state': False,
                'data': {
                    'Error': ['razorpay_payment_link_id is required']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        appointment_transaction_id = encoded_tx_id

        appointment_data = cache.get(appointment_transaction_id)
        if appointment_data is None:
            return Response({
                'state': False,
                'data': {
                    'CacheError': ['Data not found inside cache']
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        clinic = Clinic.objects.get(id=appointment_data['clinic'])

        try:
            client = razorpay.Client(auth=(RAZORPAY_CLIENT_ID, RAZORPAY_CLIENT_SECRET))
            payment_link_entity = client.payment_link.fetch(appointment_transaction_id)

            if payment_link_entity.get('status') == 'paid':

                try:
                    pending_appointment = AppointmentState.objects.get(
                        appointment=appointment_data['appointment']
                    )
                    pending_appointment.payment_status = 'completed'
                    pending_appointment.save()

                    # Update the appointment status to 'booked'
                    appointment = pending_appointment.appointment
                    appointment.appointment_status = 'booked'
                    appointment.save()

                    pending_appointment.convert_to_appointment()
                except AppointmentState.DoesNotExist:
                    logger.error(f"PendingAppointment not found for appointment {appointment_data['appointment'].id}")

                amount = round(payment_link_entity.get('amount_paid') / 100)
                procedure = Procedure.objects.filter(clinic_id=appointment_data['clinic'], name='Advance Amount').first()

                payment_type = "upi"

                # payment_instrument_type = response_data["data"].get("paymentInstrument", {}).get("type", "").upper()
                
                # if payment_instrument_type == "NETBANKING":
                #     payment_type = "netbanking"
                # elif payment_instrument_type == "UPI":
                #     payment_type = "upi"
                # elif payment_instrument_type == "CARD":
                #     payment_type = "card"

                # Check if Invoice already exists
                # invoice = Invoice.objects.filter(
                #     appointment=appointment_data['appointment'],
                #     invoice_number=appointment_data['appointment'].id,
                #     clinic_id=appointment_data['clinic']
                # ).first()

                # Check if Payment already exists
                payment = Payment.objects.filter(
                    transaction_id__endswith=appointment_transaction_id[-23:]
                ).first()

                if not payment:
                    if not create_invoice_and_payment(appointment_data, amount, procedure, payment_type, tx_id=f"S-{appointment_transaction_id[-23:]}"):
                        return Response({
                            'state': False,
                            'data': {
                                'Error': ['Error during atomic transaction']
                            }
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    patient_booking_notifications(appointment_data)

                cache.delete(appointment_transaction_id)

                clinic_details = {
                    'clinic_name': clinic.name,
                    'clinic_location': clinic.map_link,
                    'clinic_contact_number': f"+91 {str(clinic.phone_no_1)[-10:]}"
                }

                return Response({
                    'state': True,
                    'message': 'Appointment created successfully',
                    'data': clinic_details
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(traceback.format_exc())
            return Response({
                'state': False,
                'data': {
                    'Error': [str(e)]
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RefundList(generics.ListCreateAPIView):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['transaction_id', 'payment__transaction_id', 'invoice__invoice_number']

    def get_queryset(self):
        queryset = Refund.objects.all().order_by('-created_at')
        params = self.request.query_params
        if params:
            for param in params:
                if param not in ['page', 'search']:
                    queryset = queryset.filter(**{param: params[param]})
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

class InvoiceRefund(APIView):
    def post(self, request):
        try:
            data = request.data
            invoice_number = data.get('invoice_number')
            refund_amount = float(data.get('amount', 0))
            reason = data.get('reason', 'No reason provided')
            payment_data_payload = data.get('payment_data', {})
            user = request.user

            # Validate invoice exists
            try:
                invoice = Invoice.objects.get(invoice_number=invoice_number)
            except Invoice.DoesNotExist:
                return Response(
                    {'error': 'Invoice not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get all payments except paid ones for this invoice
            payments = Payment.objects.filter(invoice=invoice).exclude(
                transaction_type='paid'
            )

            # Calculate total collected amount (payments - excess amounts)
            total_collected = sum(
                payment.price - (payment.excess_amount if payment.transaction_type != 'wallet_payment' else 0)
                for payment in payments
            )

            # Calculate total already refunded
            total_refunded = Payment.objects.filter(
                invoice=invoice,
                transaction_type='paid'
            ).exclude(
                transaction_id__startswith='W-REF'
            ).aggregate(total=Sum('price'))['total'] or 0
            total_refunded = abs(total_refunded)

            # Calculate remaining refundable amount
            remaining_refundable = total_collected - total_refunded

            # Validate refund amount
            if refund_amount <= 0:
                return Response(
                    {'error': 'Refund amount must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if refund_amount > remaining_refundable:
                return Response(
                    {'error': f'Maximum refundable amount is {remaining_refundable}. Cannot refund more than the remaining invoice amount'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the latest payment for this invoice
            payment = payments.latest('created_at')

            if not payment:
                return Response(
                    {'error': 'No payment found for this invoice'},
                    status=status.HTTP_404_NOT_FOUND
                )

            with transaction.atomic():
                # Ensure transaction_id is prefixed with "W-REF-" and includes a random string
                random_string = generate_random_string()
                transaction_id_from_payload = payment_data_payload.get('transaction_id', '')
                transaction_id = f'I-REF-{random_string}-{transaction_id_from_payload}'

                # Create negative payment record
                refund_payment = Payment.objects.create(
                    invoice=invoice,
                    patient=invoice.patient,
                    clinic=invoice.clinic,
                    transaction_id=transaction_id,
                    price=-refund_amount,
                    payment_status=payment_data_payload.get('payment_status', 'success'),
                    type=payment_data_payload.get('type', payment.type),
                    mode=payment_data_payload.get('mode', payment.mode),
                    transaction_type='paid',
                    created_by=user,
                    updated_by=user,
                    collected_on=payment_data_payload.get('collected_on', timezone.now().date())
                )

                # Prepare refund data
                refund_data = {
                    'payment': refund_payment.id,
                    'invoice': invoice.id,
                    'amount': refund_amount,
                    'reason': reason,
                    'refund_date': timezone.now().date(),
                    'transaction_id': refund_payment.transaction_id,
                    'clinic': invoice.clinic.id,
                    'patient': invoice.patient.id,
                    'status': 'completed',
                    'created_by': user.id,
                    'updated_by': user.id
                }

                # Use RefundSerializer to create the refund record
                serializer = RefundSerializer(data=refund_data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(
                        {'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update invoice paid status and amount
                new_total = invoice.grand_total - refund_amount
                invoice.grand_total = new_total
                invoice.is_paid = new_total > 0
                invoice.notes = f"{invoice.notes or ''}\nRefund processed: {refund_amount} on {timezone.now().date()}"
                invoice.save()

                # Update invoice items proportionally
                invoice_items = InvoiceItems.objects.filter(invoice=invoice)
                for item in invoice_items:
                    item.price -= refund_amount
                    item.total_after_discount -= refund_amount
                    item.total -= refund_amount
                    item.updated_by = user
                    item.save()

                return Response({
                    'message': 'Refund processed successfully',
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            return Response(
                {'error': 'Failed to process refund'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class WalletRefund(APIView):
    def post(self, request):
        try:
            with transaction.atomic():
                data = request.data
                user_id = data.get('patient_id')
                amount = float(data.get('amount', 0))
                reason = data.get('reason', 'No reason provided')
                payment_data_payload = data.get('payment_data', {})

                # Validation checks remain same...
                if amount <= 0:
                    return Response(
                        {'error': 'Amount must be greater than 0'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                wallet_balance = get_user_wallet_balance(user_id)
                if wallet_balance < amount:
                    return Response(
                        {'error': 'Insufficient wallet balance'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                balance_payments = Payment.objects.filter(
                    patient=user_id,
                    balance__gt=0
                ).order_by('id')

                if not balance_payments.exists():
                    return Response(
                        {'error': 'No payments found with available balance'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                clinic_id = balance_payments.first().clinic_id
                amount_to_refund = amount
                refunded_payments = []
                refund_invoices = []  # Track invoices being refunded from

                # Process refund from each payment with balance
                for payment in balance_payments:
                    if amount_to_refund <= 0:
                        break

                    available_balance = payment.balance
                    refund_amount = min(available_balance, amount_to_refund)

                    # Update payment balance
                    payment.balance -= refund_amount
                    payment.save()

                    amount_to_refund -= refund_amount
                    refunded_payments.append({
                        'payment_id': payment.id,
                        'refund_amount': refund_amount,
                        'invoice_id': payment.invoice.id if payment.invoice else None
                    })

                    # Track invoice if exists
                    if payment.invoice and payment.invoice not in refund_invoices:
                        refund_invoices.append(payment.invoice)

                # Ensure transaction_id is prefixed with "W-REF-" and includes a random string
                random_string = generate_random_string()
                transaction_id_from_payload = payment_data_payload.get('transaction_id', '')
                transaction_id = f'W-REF-{random_string}-{transaction_id_from_payload}'

                # Create refund payment record
                payment_data = {
                    'patient_id': user_id,
                    'clinic_id': clinic_id,
                    'transaction_id': transaction_id,
                    'price': amount,
                    'payment_status': payment_data_payload.get('payment_status', 'success'),
                    'type': payment_data_payload.get('type', 'wallet'),
                    'mode': payment_data_payload.get('mode', 'offline'),
                    'transaction_type': payment_data_payload.get('transaction_type', 'paid'),
                    'excess_amount': -amount,  # Set to negative of the amount
                    'balance': 0,  # Set to 0
                    'collected_on': payment_data_payload.get('collected_on', timezone.now().date()),
                    'created_by': request.user,
                    'updated_by': request.user
                }

                # If refunding from single invoice, link it
                if len(refund_invoices) == 1:
                    payment_data['invoice'] = refund_invoices[0]

                payment = Payment.objects.create(**payment_data)
                payment.receipt_id = payment.id
                payment.save()

                # Create refund record
                refund_data = {
                    'payment': payment.id,
                    'amount': amount,
                    'status': 'completed',
                    'reason': reason,
                    'refund_date': timezone.now().date(),
                    'transaction_id': payment.transaction_id,
                    'clinic': clinic_id,
                    'patient': user_id,
                    'created_by': request.user.id,
                    'updated_by': request.user.id
                }

                # Link refund to invoice if single source
                if len(refund_invoices) == 1:
                    refund_data['invoice'] = refund_invoices[0].id

                serializer = RefundSerializer(data=refund_data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(
                        {'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                return Response({
                    'message': 'Wallet refund processed successfully',
                    'refund_amount': amount,
                    'new_balance': wallet_balance - amount,
                    'transaction_id': payment.transaction_id
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Wallet refund failed: {str(e)}")
            return Response(
                {'error': 'Failed to process wallet refund'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaymentCallbackView(APIView):
    permission_classes = []

    def post(self, request):
        encoded_response = request.data.get('response')
        response_data = base64_to_json(encoded_response)
        code = response_data.get('code')
        appointment_transaction_id = response_data.get('data', {}).get('merchantTransactionId')
        appointment_data = cache.get(appointment_transaction_id)

        if appointment_data is None:
            return Response({
                'state': False,
                'data': {
                    'CacheError': ['Data not found inside cache']
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not response_data.get('success'):
            return Response({
                'state': False,
                'code': code,
                'data': {
                    'Error': [response_data["message"]]
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if code == 'PAYMENT_SUCCESS':
            try:
                pending_appointment = AppointmentState.objects.get(
                    appointment=appointment_data['appointment']
                )
                pending_appointment.payment_status = 'completed'
                pending_appointment.save()

                # Update the appointment status to 'booked'
                appointment = pending_appointment.appointment
                appointment.appointment_status = 'booked'
                appointment.save()

                pending_appointment.convert_to_appointment()

            except AppointmentState.DoesNotExist:
                logger.error(f"PendingAppointment not found for appointment {appointment_data['appointment'].id}")
                return Response({
                    'state': False,
                    'data': {
                        'Error': ['Pending appointment not found']
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except Exception as e:
                logger.error(f"Error updating payment status: {e}")
                return Response({
                    'state': False,
                    'data': {
                        'Error': ['Error updating payment status']
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            amount = round(response_data["data"]["amount"] / 100)
            procedure = Procedure.objects.filter(clinic_id=appointment_data['clinic'], name='Advance Amount').first()

            payment_instrument_type = response_data["data"].get("paymentInstrument", {}).get("type", "").upper()
            payment_type = "upi"

            if payment_instrument_type == "NETBANKING":
                payment_type = "netbanking"
            elif payment_instrument_type == "UPI":
                payment_type = "upi"
            elif payment_instrument_type == "CARD":
                payment_type = "card"

            if not create_invoice_and_payment(appointment_data, amount, procedure, payment_type):
                return Response({
                    'state': False,
                    'data': {
                        'Error': ['Error during atomic transaction']
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'state': True,
                'message': 'Appointment created successfully',
            }, status=status.HTTP_201_CREATED)
        
# def get_phonepe_access_token():
#     url = "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token"
#     headers = {
#         "Content-Type": "application/x-www-form-urlencoded"
#     }
#     data = {
#         "client_id": "ATLASUAT_2501101539212264045568",
#         "client_version": "1",
#         "client_secret": "NmEyOWIyNjctNjBkNi00NjNjLTkwYjUtZWExYmY0OWYyZWVm",
#         "grant_type": "client_credentials"
#     }

#     response = requests.post(url, headers=headers, data=data)
#     if response.status_code == 200:
#         access_token = response.json().get("access_token")
#         return access_token
#     else:
#         raise Exception(f"Failed to obtain access token: {response.json()}")   
    
# def create_phonepe_payment_link(request):
#     try:
#         access_token = get_phonepe_access_token()
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
#     print(access_token)
#     url = "https://api-preprod.phonepe.com/apis/pg-sandbox/paylinks/v1/pay"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"O-Bearer {access_token}"
#     }
#     data = {
#         "merchantOrderId": "1",
#         "amount": 10000,
#         "paymentFlow": {
#             "type": "PAYLINK",
#             "customerDetails": {
#                 "name": "Biswarghya Biswas",
#                 "phoneNumber": "+917003435879",
#                 "email": "biswa@gmail.com"
#             },
#         }
#     }

#     response = requests.post(url, headers=headers, json=data)
#     print(response.text)
#     if response.status_code == 200:
#         paylinkUrl = response.json().get("data", {}).get("paylinkUrl")
#         return JsonResponse({"paylinkUrl": paylinkUrl})
#     else:
#         return JsonResponse({"error": response.json()}, status=response.status_code)

class RazorpayWebhookView(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        received_signature = request.headers.get('X-Razorpay-Signature')
        # Verify the webhook signature
        expected_signature = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(received_signature, expected_signature):
            # Process the webhook data
            event = data.get('event')
            payload = data.get('payload')
            payment_link_entity = payload.get('payment_link').get('entity')

            if event == 'payment_link.paid':

                if payment_link_entity.get('status') == 'paid':
                    appointment_transaction_id = payment_link_entity.get('id')
                    appointment_data = cache.get(appointment_transaction_id)

                    if appointment_data is None:
                        return Response({
                            'state': False,
                            'data': {
                                'CacheError': ['Data not found inside cache']
                            }
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    try:
                        pending_appointment = AppointmentState.objects.get(
                            appointment=appointment_data['appointment']
                        )
                        pending_appointment.payment_status = 'completed'
                        pending_appointment.save()

                        # Update the appointment status to 'booked'
                        appointment = pending_appointment.appointment
                        appointment.appointment_status = 'booked'
                        appointment.save()

                        pending_appointment.convert_to_appointment()

                    except AppointmentState.DoesNotExist:
                        logger.error(f"PendingAppointment not found for appointment {appointment_data['appointment'].id}")
                        return Response({
                            'state': False,
                            'data': {
                                'Error': ['Pending appointment not found']
                            }
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    except Exception as e:
                        logger.error(f"Error updating payment status: {e}")
                        return Response({
                            'state': False,
                            'data': {
                                'Error': ['Error updating payment status']
                            }
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    amount = round(payment_link_entity.get('amount_paid') / 100)
                    procedure = Procedure.objects.filter(clinic_id=appointment_data['clinic'], name='Advance Amount').first()


                    payment_type = "upi"

                    # payment_instrument_type = response_data["data"].get("paymentInstrument", {}).get("type", "").upper()
                    
                    # if payment_instrument_type == "NETBANKING":
                    #     payment_type = "netbanking"
                    # elif payment_instrument_type == "UPI":
                    #     payment_type = "upi"
                    # elif payment_instrument_type == "CARD":
                    #     payment_type = "card"

                    if not create_invoice_and_payment(appointment_data, amount, procedure, payment_type, tx_id=f"W-{appointment_transaction_id[-23:]}"):
                        return Response({
                            'state': False,
                            'data': {
                                'Error': ['Error during atomic transaction']
                            }
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                    patient_booking_notifications(appointment_data)

                    return Response({
                        'state': True,
                        'message': 'Appointment created successfully',
                    }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'state': False,
                    'message': 'unhandled event',
                }, status=status.HTTP_501_NOT_IMPLEMENTED)
        else:
            return Response({
                'state': False,
                'message': 'invalid signature',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CreatePayment(APIView):
    def post(self, request):
        try:
            # Add created_by and updated_by from the authenticated user
            data = request.data.copy()
            data.update({
                'created_by': request.user.id,
                'updated_by': request.user.id
            })

            serializer = PaymentSerializer(data=data)
            if serializer.is_valid():
                payment = serializer.save()
                
                # Update receipt_id to be same as payment id after creation
                Payment.objects.filter(id=payment.id).update(
                    receipt_id=payment.id
                )
                
                return Response({
                    'message': 'Payment created successfully',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'message': 'Invalid data provided',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'message': 'Error creating payment',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        