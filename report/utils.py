from django.db.models import Count, F, Avg, Q, Sum, Value, Case, DecimalField, When, CharField
from django.db.models.functions import Concat, Coalesce, TruncDate, TruncMonth
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from appointment.models import Appointment, Category, Procedure
from base.utils import convert_timedelta, price_format, str_to_date
from payment.models import Payment, Invoice, Wallet, InvoiceItems


class AppointmentReport:
    def __init__(self, clinic_id=None, from_date=None, to_date=None):
        self.clinic_id = clinic_id
        self.from_date = str_to_date(from_date, '%Y-%m-%dT%H:%M:%S',
                                     '%Y-%m-%dT00:00:00') if from_date \
            else from_date
        self.to_date = str_to_date(to_date, '%Y-%m-%dT%H:%M:%S',
                                   '%Y-%m-%dT23:59:59') if to_date else \
            to_date
        self.fdate = str_to_date(self.from_date, '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d')
        self.tdate = str_to_date(self.to_date, '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d')

    def get_appointment_filter_conditions(self, check_clinic=True,
                                          check_date=True):
        conditions = Q()
        if self.clinic_id is not None and check_clinic:
            conditions &= Q(clinic=self.clinic_id)
        if self.from_date is not None and self.to_date is not None and \
                check_date:
            conditions &= Q(
                scheduled_from__range=(self.from_date, self.to_date))
        return conditions

    def get_filter_conditions_invoice_items(self):
        conditions = Q()
        if self.fdate is not None and self.tdate is not None:
            conditions &= Q(
                created_at__range=(self.fdate, self.tdate))
        if self.clinic_id is not None:
            conditions &= Q(invoice__clinic=self.clinic_id)
        return conditions

    def get_filter_conditions_invoiceitems(self):
        conditions = Q()
        if self.fdate is not None and self.tdate is not None:
            conditions &= Q(
                invoice__date__range=(self.fdate, self.tdate))
        if self.clinic_id is not None:
            conditions &= Q(invoice__clinic=self.clinic_id)
        return conditions

    def get_filter_conditions_payment(self):
        conditions = Q()
        if self.clinic_id is not None:
            conditions &= Q(clinic=self.clinic_id)
        if self.fdate is not None and self.tdate is not None:
            conditions &= Q(
                collected_on__range=(self.fdate, self.tdate))
        return conditions

    def get_filter_conditions_invoices(self):
        conditions = Q()
        if self.fdate is not None and self.tdate is not None:
            conditions &= Q(
                date__range=(self.fdate, self.tdate))
        if self.clinic_id is not None:
            conditions &= Q(clinic=self.clinic_id)
        return conditions

    def get_filter_conditions_invoice_items(self):
        conditions = Q()
        if self.fdate is not None and self.tdate is not None:
            conditions &= Q(
                created_at__range=(self.fdate, self.tdate))
        if self.clinic_id is not None:
            conditions &= Q(invoice__clinic=self.clinic_id)
        return conditions

    def appointment_summary(self):

        count_doctors = self.get_doctors_appointments()
        # count_categories, categories_appointments =
        # self.get_categories_appointments()
        # count_procedures, procedures_appointments =
        # self.get_procedure_appointments()
        chiropractic_appointments = self.get_category_appointments_count(
            'Chiropractic')
        physiotherapy_appointments = self.get_category_appointments_count(
            'Physiotherapy')
        session_12_12_appointments = self.get_procedure_appointments_count(
            'Chiropractic '
            'Treatment Plan > '
            'Session 12/12')
        session_20_20_appointments = self.get_procedure_appointments_count(
            'Chiropractic '
            'Treatment Plan > '
            'Session 20/20')
        physiotherapy_1_12_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 1/12'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 1/12')
        
        physiotherapy_12_12_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 12/12'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 12/12')
        
        physiotherapy_1_20_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 1/20'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 1/20')
        
        physiotherapy_20_20_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 20/20'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 20/20')

        return {
            'total_appointments': self.get_total(),
            'count_of_doctors_with_appointments': count_doctors,
            'chiropractic_appointments': chiropractic_appointments,
            'physiotherapy_appointments': physiotherapy_appointments,
            'session_12_12_appointments': session_12_12_appointments,
            'session_20_20_appointments': session_20_20_appointments,
            # 'count_of_categories_appointments': count_categories,
            # 'count_of_procedures_appointments': count_procedures,
            # 'total_advance_payments': self.get_advance_payment_count(),
            'avg_waiting_time': self.get_avg_waiting_time(),
            'avg_treatment_time': self.get_avg_treatment_time(),

            'chiropractic_session_1_12':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 1/12'),
            'chiropractic_session_12_12':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 12/12'),
            'chiropractic_session_1_20':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 1/20'),
            'chiropractic_session_20_20':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 20/20'),
            'total_earnings_chiropractic_sessions': price_format(self.get_category_total_income(
                            'Chiropractic')-self.get_category_total_discount('Chiropractic')),

            'physiotherapy_sessions_1_12': physiotherapy_1_12_appointments,
            'physiotherapy_sessions_12_12': physiotherapy_12_12_appointments,
            'physiotherapy_sessions_1_20': physiotherapy_1_20_appointments,
            'physiotherapy_sessions_20_20': physiotherapy_20_20_appointments,
            'total_earnings_Physiotherapy_sessions': price_format(self.get_category_total_income(
                            'Physiotherapy')-self.get_category_total_discount('Physiotherapy')),

            'cancelled_by_doctors': self.get_cancelled_doctors_count(),
            'cancelled_by_patients': self.get_cancelled_patients_count(),
            'no_cancelled_appointments': self.get_count_on_status('cancelled'),
            'total_cost_cancelled_appointments': price_format(self.get_cancelled_appointments_earning()),
            'no_show': self.get_count_on_status('not_visited'),
            'total_cost_no_show_appointments': price_format(self.get_cost_on_status('not_visited')),

            'patients': self.get_patients_count(),
            'old_patients': self.get_old_patients(),
            'new_patients': self.get_new_patients(),
            'chiropractic_patients': self.get_unique_patients_by_category(
                'Chiropractic'),  # 'Chiropractic',
            'physiotherapy_patients': self.get_unique_patients_by_category(
                'Physiotherapy'),  # 'Physiotherapy',

            'total_income': price_format(self.get_total_income()),
            'total_discount': price_format(self.get_total_discount()),
            'total_earning': price_format(self.get_total_income()-self.get_total_discount()),
            'total_due_payment':price_format(self.get_due_amount()),
            'total_advance': price_format(self.get_total_advance()),

            'total_income_chiropractic': price_format(self.get_category_total_income('Chiropractic')),
            'total_discount_chiropractic': price_format(self.get_category_total_discount('Chiropractic')),
            'total_earning_chiropractic': price_format(self.get_category_total_income(
                            'Chiropractic')-self.get_category_total_discount('Chiropractic')),

            'total_income_physiotherapy': price_format(self.get_category_total_income('Physiotherapy')),
            'total_discount_physiotherapy': price_format(self.get_category_total_discount('Physiotherapy')),
            'total_earning_physiotherapy': price_format(self.get_category_total_income(
                            'Physiotherapy')-self.get_category_total_discount('Physiotherapy')),
        }

    def revenue_summary(self):
        return {
            'total_appointments': self.get_total(),
            'total_revenue': self.get_total_income(),
            'total_advance_payments': self.get_advance_payment_count(),
            'avg_waiting_time': self.get_avg_waiting_time(),
            'avg_treatment_time': self.get_avg_treatment_time(),

            'chiropracti_session_1_12':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 1/12'),
            'chiropracti_session_12_12':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 12/12'),
            'chiropracti_session_1_20':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 1/20'),
            'chiropracti_session_20_20':
                self.get_procedure_appointments_count('Chiropractic '
                                                        'Treatment Plan > '
                                                        'Session 20/20'),

            'total_income': price_format(self.get_total_income()+self.get_total_discount()),
            'total_discount': price_format(self.get_total_discount()),
            'total_earning': price_format((self.get_total_income()+self.get_total_discount())-self.get_total_discount()),
        }

    def income_summary(self):
        cost = self.get_total_income()
        discount = self.get_total_discount()
        total = cost + discount
        return {
            'cost': price_format(total),
            'discount': price_format(discount),
            'income_after_discount': price_format(total - discount),
            'tax': price_format(self.get_tax()),
            'invoice_amount': price_format(self.get_invoices_amount()),
        }

    def billing_summary(self):
        invoice_grand_total = self.get_total_income()
        discount = self.get_total_discount()
        total = invoice_grand_total + discount
        payment = self.get_total_payments()
        # due_amount = invoice_grand_total - payment
        total_due = self.get_due_amount()

        return {
            'total_income': price_format(total),
            'total_discount': price_format(discount),
            'total_after_discount': price_format(invoice_grand_total),
            'total_dues': price_format(total_due),
            'total_payments': price_format(payment),
        }

    def get_total(self):
        total = Appointment.objects.filter(
            self.get_appointment_filter_conditions()
        ).count()
        return total

    def get_category_appointments_count(self, category_name):
        total_cat_appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            category__name=category_name
        ).count()
        return total_cat_appointments
        
    def get_category_total_income(self, category_name):
        total_revenue = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
            appointment__category__name=category_name
        ).aggregate(
            total_revenue=Sum('grand_total', default=0)
        )
        return total_revenue['total_revenue']
    
    def get_category_total_discount(self, category_name):
        invoices = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
            appointment__category__name=category_name
        ).aggregate(
            total_discount=Sum('invoiceitems__discount', default=0)
        )
        return invoices['total_discount']

    def get_procedure_appointments_count(self, procedure_name):
        total_cat_appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            procedure__name=procedure_name
        ).count()
        return total_cat_appointments

    def get_procedure_appointments_income(self, procedure_name):
        appointments = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
            appointment__procedure__name=procedure_name
        ).aggregate(
            total_revenue=Sum('grand_total', default=0)
        )
        return appointments['total_revenue']
    
    def get_procedure_total_discount(self, procedure_name):
        invoices = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
            appointment__procedure__name=procedure_name
        ).aggregate(
            total_discount=Sum('invoiceitems__discount', default=0)
        )
        return invoices['total_discount']
    
    def get_cancelled_appointments_earning(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status__in=['cancelled', 'not_visited']
        ).aggregate(total_earnings=Sum('procedure__cost', default=0))
        return appointments['total_earnings']

    def get_avg_treatment_time(self):
        avg_treatment_time = Appointment.objects.filter(
            self.get_appointment_filter_conditions()
        ).annotate(
            treatment_time=F('checked_out') - F('engaged_at')
        ).aggregate(avg_treatment_time=Avg('treatment_time'))
        return convert_timedelta(avg_treatment_time['avg_treatment_time'])

    def get_advance_payment_count(self):
        total_advance_payments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            Q(
                Q(payment_status='collected') | Q(
                    payment_status='partial_paid'),
            )
        ).count()
        return total_advance_payments

    def get_avg_waiting_time(self):
        avg_waiting_time = Appointment.objects.filter(
            self.get_appointment_filter_conditions()
        ).annotate(
            waiting_time=F('engaged_at') - F('checked_in')
        ).aggregate(avg_waiting_time=Avg('waiting_time'))
        return convert_timedelta(avg_waiting_time['avg_waiting_time'])

    def get_doctors_appointments(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
        ).aggregate(
            total_appointments=Count('doctor', unique=True)
        )
        return appointments['total_appointments']

    def get_categories_appointments(self):
        categories_appointments = Category.objects.exclude(
            appointment__isnull=True
        ).annotate(
            total_appointments=Count('appointment',
                                     filter=self.get_appointment_filter_conditions())
        )

        return categories_appointments.count(), categories_appointments

    def get_procedures_appointments(self):

        procedures_appointments = Procedure.objects.exclude(
            appointment__isnull=True
        ).annotate(
            total_appointments=Count('appointment',
                                     filter=self.get_appointment_filter_conditions())
        )

        return procedures_appointments.count(), procedures_appointments

    def get_cancelled_appointments(self):
        cancelled_appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status='cancelled'
        ).count()
        return cancelled_appointments

    # def get_total_income(self):
    #     total_revenue = Invoice.objects.filter(
    #         self.get_filter_conditions_invoices(),
    #     ).aggregate(
    #         total_revenue=Sum('grand_total', default=0)
    #     )
    #     return total_revenue['total_revenue']
    
    def get_total_income(self):
        total_revenue = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
        ).aggregate(
            total_revenue=Sum('invoiceitems__total_after_discount', default=0)
        )
        return total_revenue['total_revenue']

    def get_total_advance(self):
        # invoices = Invoice.objects.filter(
        #     self.get_filter_conditions_invoices(),
        # )
        # total_amount = invoices.aggregate(
        #     total_amount=Sum('grand_total', default=0)
        # )['total_amount']
        #
        # wallet_payments = Wallet.objects.filter(
        #     invoice__in=invoices
        # ).aggregate(
        #     total=Sum('amount', default=0)
        # )['total']
        #
        # paid = self.get_total_payments()
        #
        # return max(0, (paid + wallet_payments - total_amount))
        balance = Payment.objects.filter(
            self.get_filter_conditions_payment(),
            transaction_type='collected'
        ).aggregate(
            total=Sum('excess_amount', default=0)
        )['total']
        return balance

    def get_due_amount(self):
        invoices = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
            appointment__payment_status='partial_paid'
        )
        partial_paid = invoices.aggregate(
            total_due_amount=Sum('grand_total', default=0)
        )
        invoice_payments = Payment.objects.filter(
            invoice__in=invoices
        ).aggregate(
            total=Sum('price', default=0)
        )
        wallet_payments = Wallet.objects.filter(
            invoice__in=invoices
        ).aggregate(
            total=Sum('amount', default=0)
        )
        payments = invoice_payments['total'] + wallet_payments['total']
        return partial_paid['total_due_amount'] - payments

    def get_cancelled_doctors_count(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status='cancelled',
            updated_by__groups__name='doctor'
        ).aggregate(
            cancelled_doctors_count=Count('doctor')
        )
        return appointments['cancelled_doctors_count']

    def get_cancelled_patients_count(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status='cancelled',
        ).exclude(
            updated_by__groups__name='doctor'
        ).aggregate(
            cancelled_patients_count=Count('patient')
        )
        return appointments['cancelled_patients_count']

    def get_count_on_no_show(self, status):
        return Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status=status
        ).count()
    
    def get_count_on_status(self, statuses):
        return Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status__in=statuses
        ).count()

    def get_cost_on_status(self, status):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status=status
        ).annotate(
            total_cost=Sum('procedure__cost', default=0)
        ).aggregate(total=Sum('total_cost', default=0))
        return appointments['total']
    
    def get_cost_on_cancelled_by_patient(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status='cancelled',
        ).exclude(
            updated_by__groups__name='doctor'
        ).annotate(
            total_cost=Sum('procedure__cost', default=0)
        ).aggregate(total=Sum('total_cost', default=0))
        return appointments['total']
    
    def get_cost_on_cancelled_by_doctor(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            appointment_status='cancelled',
            updated_by__groups__name='doctor'
        ).annotate(
            total_cost=Sum('procedure__cost', default=0)
        ).aggregate(total=Sum('total_cost', default=0))
        return appointments['total']

    def get_patients_count(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
        ).aggregate(
            total_patients=Count('patient', distinct=True)
        )
        return appointments['total_patients']

    def get_old_patients(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            #is_new=False,
            #Q(
             #   Q(is_new='False') | Q(
             #       is_new='True'),
            #)
        ).exclude(is_new=True).aggregate(
            total_patients=Count('patient', distinct=True)
        )
        return appointments['total_patients']

    def get_new_patients(self):
        appointments = Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            is_new=True
        ).aggregate(
            total_patients=Count('patient', distinct=True)
        )
        return appointments['total_patients']

    def get_unique_patients_by_category(self, category_name):
        return Appointment.objects.filter(
            self.get_appointment_filter_conditions(),
            category__name=category_name
        ).distinct('patient').count()

    def get_total_discount(self):
        invoices = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
        ).aggregate(
            total_discount=Sum('invoiceitems__discount', default=0)
        )
        return invoices['total_discount']

    def get_total_earning(self):
        invoices = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
        ).aggregate(total_earning=Sum('payment__price', default=0))
        return invoices['total_earning']

    def get_total_payments(self):
        collected = Payment.objects.filter(
            self.get_filter_conditions_payment(),
            transaction_type='collected',
        ).aggregate(total=Sum('price', default=0))

        paid = Payment.objects.filter(
            self.get_filter_conditions_payment(),
            transaction_type='paid',
        ).aggregate(total=Sum('price', default=0))

        return collected['total'] + paid['total']

    # def get_advance_payment(self):
    #     total = self.get_total_payments()
    #     invoice_payments = get_total_income
    #     invoices = Invoice.objects.filter(
    #         self.get_filter_conditions_invoices(),
    #     ).aggregate(grand_total=Sum('grand_total', default=0))
    #     advance = total - invoices['grand_total']
    #     return advance > 0 and advance or 0

    def payment_summary(self):
        return {
            'total_advance_payments': price_format(self.get_total_advance()),
            'total_payments': price_format(self.get_total_payments()),
        }

    def payment_mode_summary(self, request):
        payment_mode = Payment.objects.filter(
            self.get_filter_conditions_payment(),
        ).exclude(
            type='wallet'
        ).values('type').annotate(
            total=Sum('price', default=0)
        )
        total = price_format(payment_mode.aggregate(overall=Sum('total'))['overall'] or 0)

        for invoice in payment_mode:
            invoice['total'] = price_format(invoice['total'])

        payment_mode_list = list(payment_mode)
        payment_mode_list.insert(0,{
        'type': 'Total',
        'total': total
        })

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(payment_mode_list, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    def get_invoices_amount(self):
        invoices = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
        ).aggregate(grand_total=Sum('grand_total', default=0))
        return invoices['grand_total']

    def earnings_per_procedure(self, request):
        income = self.get_total_earning()
        discount = self.get_total_discount()
        earnings = income - discount
        invoice = Invoice.objects.filter(
            self.get_filter_conditions_invoices(),
        ).annotate(
            cost=Sum('invoiceitems__price', default=0),
            total_discount=Sum('invoiceitems__discount', default=0),
            income=Sum('invoiceitems__total_after_discount', default=0),
        ).values('appointment__procedure__name', 'cost', 'total_discount', 'income')
        data = {
            'total_income': income,
            'total_discount': discount,
            'total_earnings': earnings,
            'table': invoice
        }
        page = request.GET.get('page', 1)
        paginator = Paginator(data, 50)

        try:
            paginated_result_list = paginator.page(page)
        except PageNotAnInteger:
            paginated_result_list = paginator.page(1)
        except EmptyPage:
            paginated_result_list = paginator.page(paginator.num_pages)

        return paginated_result_list.object_list

    def appointments_per_doctor(self, request):
        appoinment = Appointment.objects.filter(
            self.get_appointment_filter_conditions()
        ).exclude(appointment_status__in=['not_visited', 'cancelled']).values(
            name=Concat(F('doctor__first_name'), Value(' '), F('doctor__last_name'))
        ).annotate(
            appointments=Count('id'),
            attended=Count('id', filter=Q(appointment_status='checked_out')),
            cancelled=Count('id', filter=Q(appointment_status='cancelled')),
            no_show=Count('id', filter=Q(appointment_status='not_visited'))
        )

    # Calculate totals
        total_data = appoinment.aggregate(
            total_appointments=Sum('appointments'),
            total_attended=Sum('attended'),
            total_cancelled=Sum('cancelled'),
            total_no_show=Sum('no_show')
        )

        total_row = {
            'name': 'Total',
            'appointments': total_data['total_appointments'] or 0,
            'attended': total_data['total_attended'] or 0,
            'cancelled': total_data['total_cancelled'] or 0,
            'no_show': total_data['total_no_show'] or 0,
        }

    # Convert QuerySet to list for pagination
        appoinment_list = list(appoinment)

    # Add total at the beginning of the results
        appoinment_list.insert(0, total_row)

    # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(appoinment_list, page_size)
        page_number = int(request.GET.get('page', 1))

        try:
            paginated_data = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    def invoiced_income_per_doctor(self, request):
        conditions = self.get_filter_conditions_invoiceitems()
        invoice_items = InvoiceItems.objects.filter(
            conditions
        ).values(
            name=Concat(F('invoice__appointment__doctor__first_name'), Value(' '), F('invoice__appointment__doctor__last_name'), output_field=CharField())
        ).annotate(
            cost=Sum('price', default=0),
            discounts=Sum('discount', default=0),
            income=Sum('total_after_discount', default=0),
            tax=Sum('tax_amount', default=0),
            invoice=Sum('total_after_discount', default=0)
        ).order_by('-name')

    # Format price fields
        for item in invoice_items:
            item['cost'] = price_format(item['cost'])
            item['discounts'] = price_format(item['discounts'])
            item['income'] = price_format(item['income'])
            item['tax'] = price_format(item['tax'])
            item['invoice'] = price_format(item['invoice'])

    # Calculate totals
        total_data = invoice_items.aggregate(
            total_cost=Sum('cost'),
            total_discounts=Sum('discounts'),
            total_income=Sum('income'),
            total_tax=Sum('tax'),
            total_invoice=Sum('invoice')
        )

        total_row = {
            'name': 'Total',
            'cost': price_format(total_data['total_cost']),
            'discounts': price_format(total_data['total_discounts']),
            'income': price_format(total_data['total_income']),
            'tax': price_format(total_data['total_tax']),
            'invoice': price_format(total_data['total_invoice']),
        }

    # Convert QuerySet to list for pagination
        invoice_items_list = list(invoice_items)

    # Add total row at the beginning
        invoice_items_list.insert(0, total_row)

    # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(invoice_items_list, page_size)
        page_number = int(request.GET.get('page', 1))

        try:
            paginated_data = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }


    def get_tax(self):
        invoices = InvoiceItems.objects.select_related('invoice').filter(
            self.get_filter_conditions_invoiceitems(),
        ).aggregate(tax=Sum('tax_amount', default=0))
        return invoices['tax']

    def payments_per_day(self, request):
    # Get daily aggregations
        daily_payments = Payment.objects.filter(
            self.get_filter_conditions_payment(),
            transaction_type='collected',
            payment_status='success'
        ).values('collected_on').annotate(
            upi_total=Sum(Case(When(type='upi', then='price'), output_field=DecimalField()), default=0.0),
            card_total=Sum(Case(When(type='card', then='price'), output_field=DecimalField()), default=0.0),
            cash_total=Sum(Case(When(type='cash', then='price'), output_field=DecimalField()), default=0.0),
            net_banking_total=Sum(Case(When(type='netbanking', then='price'), output_field=DecimalField()), default=0.0),
            wallet_total=Sum(Case(When(type='wallet', then='price'), output_field=DecimalField()), default=0.0),
            total=Sum('price')
        ).order_by('collected_on')

    # Calculate overall totals
        overall_totals = Payment.objects.filter(
            self.get_filter_conditions_payment(),
            transaction_type='collected',
            payment_status='success'
        ).aggregate(
            upi_total=Sum(Case(When(type='upi', then='price'), output_field=DecimalField()), default=0.0),
            card_total=Sum(Case(When(type='card', then='price'), output_field=DecimalField()), default=0.0),
            cash_total=Sum(Case(When(type='cash', then='price'), output_field=DecimalField()), default=0.0),
            net_banking_total=Sum(Case(When(type='netbanking', then='price'), output_field=DecimalField()), default=0.0),
            wallet_total=Sum(Case(When(type='wallet', then='price'), output_field=DecimalField()), default=0.0),
            total=Sum('price')
        )

    # Format the daily report
        daily_report = [
            {
                "date": payment['collected_on'],
                "upi": price_format(payment['upi_total']),
                "card": price_format(payment['card_total']),
                "cash": price_format(payment['cash_total']),
                "net_banking": price_format(payment['net_banking_total']),
                "wallet": price_format(payment['wallet_total']),
                "total": price_format(payment['total']),
            } for payment in daily_payments
        ]

    # Format the overall totals
        overall_report = {
            "date": "Total",
            "upi": price_format(overall_totals['upi_total']),
            "card": price_format(overall_totals['card_total']),
            "cash": price_format(overall_totals['cash_total']),
            "net_banking": price_format(overall_totals['net_banking_total']),
            "wallet": price_format(overall_totals['wallet_total']),
            "total": price_format(overall_totals['total']),
        }

    # Combine daily report with overall totals
        report = [overall_report] + daily_report

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(report, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }
    
    def get_income_per_procedure(self, request):
        invoice_items = InvoiceItems.objects.filter(
            self.get_filter_conditions_invoiceitems()
        ).values(
            procedure__name=F('procedure__name')
        ).annotate(
            cost=Coalesce(Sum('price'), Value(0.0)),
            total_discount=Coalesce(Sum('discount'), Value(0.0)),
            income=Coalesce(Sum('total_after_discount'), Value(0.0))
        )
        
        invoice_items_list = list(invoice_items)
        procedure_aggregates = {}

        total_cost = 0.0
        total_discount = 0.0
        total_income = 0.0

        for item in invoice_items_list:
            if 'Chiropractic' in item['procedure__name']: #separates for chiropractic
                main_procedure_name = item['procedure__name'].split(' ')[0].strip()

            elif 'Physiotherapy' in item['procedure__name']: #separates for physiotherapy
                main_procedure_name = item['procedure__name'].split(' ')[0].strip()

            elif 'Dry' in item['procedure__name']:
                parts = item['procedure__name'].split(' ', 2)  # Split into at most 3 parts
                if len(parts) > 1:  # Ensure there are at least two parts
                    main_procedure_name = ' '.join(parts[:2]).strip()  # Combine the first two parts
                else:
                    main_procedure_name = item['procedure__name']  # Fallback if there aren't enough parts

            else:
                main_procedure_name = item['procedure__name']

            if main_procedure_name in procedure_aggregates:
                procedure_aggregates[main_procedure_name]['cost'] += item['cost']
                procedure_aggregates[main_procedure_name]['total_discount'] += item['total_discount']
                procedure_aggregates[main_procedure_name]['income'] += item['income']
            else:
                procedure_aggregates[main_procedure_name] = {
                'cost': item['cost'],
                'total_discount': item['total_discount'],
                'income': item['income'],
                }

            total_cost += item['cost']
            total_discount += item['total_discount']
            total_income += item['income']

        result_list = []
        result_list.append({
            's.no.': '',
            'procedure': 'Total',
            'cost': price_format(total_cost),
            'discount': price_format(total_discount),
            'income': price_format(total_income),
        })

        for index, (procedure_name, aggregates) in enumerate(procedure_aggregates.items(), start=1):
            result_list.append({
                's.no.': index,
                'procedure': procedure_name,
                'cost': price_format(aggregates['cost']),
                'discount': price_format(aggregates['total_discount']),
                'income': price_format(aggregates['income']),
            })

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(result_list, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    def get_appointment_procedure(self, request):
        appointments = (
            Appointment.objects.filter(self.get_appointment_filter_conditions()).exclude(appointment_status__in=['not_visited', 'cancelled'])
            .annotate(
            procedure_name=Coalesce('procedure__name', Value('Procedure'))
            )
            .values('procedure_name')
            .annotate(count=Count('procedure_name'))
        )

        procedure_aggregates = {}
        for item in appointments:
            if 'Chiropractic' in item['procedure_name']:
                main_procedure_name = item['procedure_name'].split(' ')[0].strip()

            elif 'Physiotherapy' in item['procedure_name']:
                main_procedure_name = item['procedure_name'].split(' ')[0].strip()

            elif 'Dry' in item['procedure_name']:
                parts = item['procedure_name'].split(' ', 2)  # Split into at most 3 parts
                if len(parts) > 1:  # Ensure there are at least two parts
                    main_procedure_name = ' '.join(parts[:2]).strip()  # Combine the first two parts
                else:
                    main_procedure_name = item['procedure_name']  # Fallback if there aren't enough parts

            else:
                main_procedure_name = item['procedure_name']
        
            if main_procedure_name in procedure_aggregates:
                procedure_aggregates[main_procedure_name] += item['count']
            else:
                procedure_aggregates[main_procedure_name] = item['count']

        total_count = 0
        result_list = []
        for index, (name, count) in enumerate(procedure_aggregates.items(), start=1):
            result_list.append({'s.no.': index, 'procedure': name, 'count': count})
            total_count += count

        result_list.insert(0, {'s.no.': '', 'procedure': 'Total', 'count': total_count})
        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(result_list, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    def get_advance_payments(self, request):
        payment = list(Payment.objects.filter(
            self.get_filter_conditions_payment(),
        ).values(
            name=Concat(F('patient__first_name'), Value(' '
                                                            ), F('patient__last_name')),
            Id=F('patient__atlas_id')
        ).annotate(
            received=Sum('price', default=0),
            deducted=Sum('balance', default=0),
            Balance=Sum('excess_amount', default=0),
            due=Sum('balance', default=0)
        ).values('Id','name', 'received', 'deducted', 'Balance', 'due'))

        total_received = price_format(sum(item['received'] for item in payment))
        total_deducted = price_format(sum(item['deducted'] for item in payment))
        total_balance = price_format(sum(item['Balance'] for item in payment))
        total_due = price_format(sum(item['due'] for item in payment))
    
    # Append the total count as a dictionary to the list
        payment.insert(0,{'s.no.': "","name":"Total","Id":"","received": total_received, "deducted":total_deducted, "Balance": total_balance, "due": total_due})

        invoice_list = list(payment)
    
    # Add serial number to each entry in the list
        result_list = []
        for index, invoice in enumerate(invoice_list, start=0):
        # Create a new dictionary with 's.no' first
            invoice_with_serial = {'s.no.': index}
            invoice['received'] = price_format(invoice['received'])
            invoice['deducted'] = price_format(invoice['deducted'])
            invoice['Balance'] = price_format(invoice['Balance'])
            invoice['due'] = price_format(invoice['due'])
        
        # Add the remaining fields to the dictionary
            invoice_with_serial.update(invoice)
        
            result_list.append(invoice_with_serial)

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(result_list, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    def get_appointment(self, request):
        appointment=self.get_appointment_procedure(request)
        return appointment

    def get_cancellations(self, request):
        total=self.get_count_on_status(['cancelled','not_visited'])
        no_show=self.get_count_on_no_show('not_visited')
        cancelled_by_doctors= self.get_cancelled_doctors_count()
        cancelled_by_patients=self.get_cancelled_patients_count()
        total_cost_cancelled_appointments= price_format(self.get_cancelled_appointments_earning())
        total_cost_no_show_appointments=price_format(self.get_cost_on_status('not_visited'))
        total_cost_cancelled_by_doctor=price_format(self.get_cost_on_cancelled_by_doctor())
        total_cost_cancelled_by_patient=price_format(self.get_cost_on_cancelled_by_patient())


        data = [
        {'s.no': '', 'type': 'Total', 'count': total, 'total cost':total_cost_cancelled_appointments},
        {'s.no': '1', 'type': 'no show', 'count': no_show, 'total cost':total_cost_no_show_appointments},
        {'s.no': '2', 'type': 'cancelled by doctors', 'count': cancelled_by_doctors, 'total cost':total_cost_cancelled_by_doctor},
        {'s.no': '3', 'type': 'cancelled by patients', 'count': cancelled_by_patients, 'total cost':total_cost_cancelled_by_patient},
    ]

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(data, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }
    
    def get_daily_appointments(self, request):
        appointments_by_day = (
        Appointment.objects.filter(
            self.get_appointment_filter_conditions()).exclude(appointment_status__in=['not_visited', 'cancelled'])
        .annotate(day=TruncDate('scheduled_from'))
        .values('day')
        .annotate(total_appointments=Count('id'))
        .order_by('day')
        )
    
        response_data = []
        overall_total = 0
    
        total_appointments = sum([item['total_appointments'] for item in appointments_by_day])
        response_data.append({
        "s.no": "",
        "day": "Total",
        "total appointments": total_appointments
        })
    
        for index, item in enumerate(appointments_by_day, start=1):
            response_data.append({
            "s.no": index,
            "day": item['day'].strftime('%d %b %Y'),
            "total appointments": item['total_appointments']
        })
            overall_total += item['total_appointments']

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(response_data, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    def get_monthly_appointments(self, request):
        appointments_by_month = Appointment.objects.filter(
            self.get_appointment_filter_conditions()
        ).exclude(appointment_status__in=['not_visited', 'cancelled']).annotate(month=TruncMonth('scheduled_from')
            ).values('month'
            ).annotate(total_appointments=Count('id')
            ).order_by('month')

        response_data = []
    
        total_appointments = sum([item['total_appointments'] for item in appointments_by_month])
        response_data.append({
        "s.no": "",
        "month": "Total",
        "total appointments": total_appointments
        })
    
        for index, item in enumerate(appointments_by_month, start=1):
            formatted_month = item['month'].strftime('%B %Y')  # Format to 'Month YYYY'
            response_data.append({
            "s.no": index,
            "month": formatted_month,
            "total appointments": item['total_appointments']
            })

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(response_data, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }


    def get_appointment_plans(self, request):
        physiotherapy_1_12_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 1/12'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 1/12')
        
        physiotherapy_12_12_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 12/12'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 12/12')
        
        physiotherapy_1_20_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 1/20'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 1/20')
        
        physiotherapy_20_20_appointments = self.get_procedure_appointments_count('Physiotherapy Plus - 20/20'
                                                            ) + self.get_procedure_appointments_count(
                                                                       'Physiotherapy Standard - 20/20')

        data= [
            {'s.no': '1', 'procedure name':'chiropractic 1/12', 'total appointments':self.get_procedure_appointments_count('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 1/12'), 'total earnings': price_format(self.get_procedure_appointments_income('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 1/12')- self.get_procedure_total_discount('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 1/12'))},
            {'s.no': '2', 'procedure name':'chiropractic 12/12', 'total appointments':self.get_procedure_appointments_count('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 12/12'), 'total earnings': price_format(self.get_procedure_appointments_income('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 12/12') - self.get_procedure_total_discount('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 12/12'))},
            {'s.no': '3', 'procedure name':'chiropractic 1/20', 'total appointments':self.get_procedure_appointments_count('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 1/20'), 'total earnings': price_format(self.get_procedure_appointments_income('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 1/20')- self.get_procedure_total_discount('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 1/20'))},
            {'s.no': '4', 'procedure name':'chiropractic 20/20', 'total appointments':self.get_procedure_appointments_count('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 20/20'), 'total earnings': price_format(self.get_procedure_appointments_income('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 20/20')- self.get_procedure_total_discount('Chiropractic '
                                                                                                                         'Treatment Plan > '
                                                                                                                         'Session 20/20'))},

            {'s.no': '5', 'procedure name':'physiotherapy 1/12', 'total appointments': physiotherapy_1_12_appointments, 'total earnings': price_format((self.get_procedure_appointments_income('Physiotherapy Plus - 1/12'
                                                            ) + self.get_procedure_appointments_income(
                                                                       'Physiotherapy Standard - 1/12'))-(self.get_procedure_total_discount('Physiotherapy Plus - 1/12'
                                                            ) + self.get_procedure_total_discount(
                                                                       'Physiotherapy Standard - 1/12')))},
            {'s.no': '6', 'procedure name':'physiotherapy 12/12', 'total appointments': physiotherapy_12_12_appointments, 'total earnings': price_format((self.get_procedure_appointments_income('Physiotherapy Plus - 12/12'
                                                            ) + self.get_procedure_appointments_income(
                                                                       'Physiotherapy Standard - 12/12')))},
            {'s.no': '7', 'procedure name':'physiotherapy 1/20', 'total appointments': physiotherapy_1_20_appointments, 'total earnings': price_format((self.get_procedure_appointments_income('Physiotherapy Plus - 1/20'
                                                            ) + self.get_procedure_appointments_income(
                                                                       'Physiotherapy Standard - 1/20')))},
            {'s.no': '8', 'procedure name':'physiotherapy 20/20', 'total appointments': physiotherapy_20_20_appointments, 'total earnings': price_format((self.get_procedure_appointments_income('Physiotherapy Plus - 20/20'
                                                            ) + self.get_procedure_appointments_income(
                                                                       'Physiotherapy Standard - 20/20')))},
            ]
        
        total_appointments = sum(item['total appointments'] for item in data if 'total appointments' in item)
        data.insert(0, {'s.no': '', 'procedure name': 'Total', 'total appointments': total_appointments, 'total earnings': price_format((self.get_procedure_appointments_income('Chiropractic Treatment Plan > Session 1/12') - self.get_procedure_total_discount('Chiropractic Treatment Plan > Session 1/12'
                                                                                                                        ) + self.get_procedure_appointments_income('Chiropractic Treatment Plan > Session 12/12') - self.get_procedure_total_discount('Chiropractic Treatment Plan > Session 12/12'
                                                                                                                        ) + self.get_procedure_appointments_income('Chiropractic Treatment Plan > Session 20/20') - self.get_procedure_total_discount('Chiropractic Treatment Plan > Session 20/20'
                                                                                                                        ) + self.get_procedure_appointments_income('Chiropractic Treatment Plan > Session 1/20') - self.get_procedure_total_discount('Chiropractic Treatment Plan > Session 1/20'
                                                                                                                        ) + (self.get_procedure_appointments_income('Physiotherapy Plus - 1/12') + self.get_procedure_appointments_income('Physiotherapy Standard - 1/12')
                                                                                                                        )-(self.get_procedure_total_discount('Physiotherapy Plus - 1/12') + self.get_procedure_total_discount('Physiotherapy Standard - 1/12'))
                                                                                                                         + (self.get_procedure_appointments_income('Physiotherapy Plus - 12/12') + self.get_procedure_appointments_income('Physiotherapy Standard - 12/12')
                                                                                                                        )-(self.get_procedure_total_discount('Physiotherapy Plus - 12/12') + self.get_procedure_total_discount('Physiotherapy Standard - 12/12'))
                                                                                                                         + (self.get_procedure_appointments_income('Physiotherapy Plus - 1/20') + self.get_procedure_appointments_income('Physiotherapy Standard - 1/20')
                                                                                                                        )-(self.get_procedure_total_discount('Physiotherapy Plus - 1/20') + self.get_procedure_total_discount('Physiotherapy Standard - 1/20'))
                                                                                                                        + (self.get_procedure_appointments_income('Physiotherapy Plus - 20/20') + self.get_procedure_appointments_income('Physiotherapy Standard - 20/20')
                                                                                                                        )-(self.get_procedure_total_discount('Physiotherapy Plus - 20/20') + self.get_procedure_total_discount('Physiotherapy Standard - 20/20'))
                                                                                                                        ))})
        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(data, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }

    
    def get_daily_patient(self, request):
        appointment_filter_conditions = self.get_appointment_filter_conditions()
        base_appointments = Appointment.objects.filter(appointment_filter_conditions
        ).annotate(day=TruncDate('scheduled_from')
        ).values('day').order_by('day')

        patient_stats = base_appointments.annotate(
            total_patients=Count('patient', distinct=True),
            new_patients=Count('patient', distinct=True, filter=Q(is_new=True)),
            old_patients = Count('patient', distinct=True, filter=Q(is_new=False) | Q(is_new__isnull=True))
        )

        response_data = [
            {
                "s.no": index,
                "day": item['day'].strftime('%d %b %Y'),
                "total patients": item['total_patients'],
                "new patients": item['new_patients'],
                "old patients": item['old_patients']
            }
            for index, item in enumerate(patient_stats, start=1)
        ]

        total_patient = sum(item['total_patients'] for item in patient_stats)
        total_new_patients = sum(item['new_patients'] for item in patient_stats)
        total_old_patients = sum(item['old_patients'] for item in patient_stats)

        response_data.insert(0, {
            "s.no": "",
            "day": "Total",
            "total patients": total_patient,
            "new patients": total_new_patients,
            "old patients": total_old_patients
        })

        # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(response_data, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }
    
    def get_monthly_patient(self, request):
        appointment_filter_conditions = self.get_appointment_filter_conditions()
        base_appointments = Appointment.objects.filter(appointment_filter_conditions).annotate(
            month=TruncMonth('scheduled_from')
        ).values('month').order_by('month')

        patient_stats = base_appointments.annotate(
            total_patients=Count('patient'),
            new_patients=Count('patient', filter=Q(is_new=True)),
            old_patients = Count('patient', filter=Q(is_new=False) | Q(is_new__isnull=True))
        )

        response_data = [
            {
                "s.no": index,
                "month": item['month'].strftime('%B %Y'),
                "total patients": item['total_patients'],
                "new patients": item['new_patients'],
                "old patients": item['old_patients']
            }
            for index, item in enumerate(patient_stats, start=1)
        ]

        total_patients = sum(item['total_patients'] for item in patient_stats)
        total_new_patients = sum(item['new_patients'] for item in patient_stats)
        total_old_patients = sum(item['old_patients'] for item in patient_stats)

        response_data.insert(0, {
            "s.no": "",
            "month": "Total",
            "total patients": total_patients,
            "new patients": total_new_patients,
            "old patients": total_old_patients
        })

    # Implement pagination
        page_size = int(request.GET.get('page_size', 20))  # Default to 20 items per page
        paginator = Paginator(response_data, page_size)
        page_number = int(request.GET.get('page', 1))
        paginated_data = paginator.get_page(page_number)

    # Build pagination info
        pagination_info = {
            "next": paginated_data.has_next(),
            "previous": paginated_data.has_previous(),
            "count": paginator.count,
            "page_size": page_size,
            "current_page": paginated_data.number,
            "pages": paginator.num_pages,
        }

    # Construct the final response
        return {
            "pagination": pagination_info,
            "results": list(paginated_data)
        }
