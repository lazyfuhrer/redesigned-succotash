from django.db.models import Sum
from rest_framework import serializers

from appointment.models import Procedure
from clinic.serializers import ClinicSerializer
from user.models import User
from .models import Invoice, InvoiceItems, Payment, Wallet, WalletPayment, Refund
from django.contrib.auth import get_user_model


class InvoiceAllSerializer(serializers.ModelSerializer):
    due_amount = serializers.SerializerMethodField(read_only=True)
    paid_amount = serializers.SerializerMethodField(read_only=True)
    advance_amount = serializers.SerializerMethodField(read_only=True)
    clinic_name = serializers.StringRelatedField(source='clinic.name')

    class Meta:
        model = Invoice
        fields = (
            'date',
            'clinic',
            'clinic_name',
            'invoice_number',
            'patient',
            'grand_total',
            'appointment',
            'notes',
            'due_amount',
            'paid_amount',
            'advance_amount'
        )

    def get_due_amount(self, obj):
        paid = Payment.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('price', default=0))['paid']
        wallet_paid = Wallet.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('amount', default=0))['paid']
        if wallet_paid:
            paid = paid + wallet_paid
        return obj.grand_total - paid if obj.grand_total - paid > 0 and \
                                         obj.appointment.payment_status != \
                                         'collected' else 0

    def get_paid_amount(self, obj):
        paid = Payment.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('price', default=0))['paid']
        wallet_paid = Wallet.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('amount', default=0))['paid']
        return paid + wallet_paid

    def get_advance_amount(self, obj):
        paid_amount = self.get_paid_amount(obj)
        return paid_amount - obj.grand_total if paid_amount > obj.grand_total else 0


class InvoiceSerializer(serializers.ModelSerializer):
    from user.serializers import PatientInfoSerializer
    items = serializers.SerializerMethodField(read_only=True)
    procedure_names = serializers.SerializerMethodField(read_only=True)
    due_amount = serializers.SerializerMethodField(read_only=True)
    paid_amount = serializers.SerializerMethodField(read_only=True)
    advance_amount = serializers.SerializerMethodField(read_only=True)
    payment = serializers.SerializerMethodField(read_only=True)
    wallet = serializers.SerializerMethodField(read_only=True)
    payment_amount = serializers.SerializerMethodField(read_only=True)
    wallet_amount = serializers.SerializerMethodField(read_only=True)
    patient_name = serializers.SerializerMethodField(read_only=True)
    patient_id = serializers.StringRelatedField(source='patient.id')
    patient_atlas_id = serializers.StringRelatedField(source='patient.atlas_id')
    cost = serializers.SerializerMethodField(read_only=True)
    discount = serializers.SerializerMethodField(read_only=True)
    tax = serializers.SerializerMethodField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    clinic_name = serializers.StringRelatedField(source='clinic.name')
    clinic_data = ClinicSerializer(source='clinic', read_only=True)
    patient_data = PatientInfoSerializer(source='patient', read_only=True)

    class Meta:
        model = Invoice
        fields = (
            'id',
            'appointment',
            'patient_name',
            'patient_id',
            'patient_atlas_id',
            'patient',
            'clinic',
            'clinic_name',
            'clinic_data',
            'invoice_number',
            'items',
            'procedure_names',
            'date',
            'grand_total',
            'notes',
            'due_amount',
            'advance_amount',
            'paid_amount',
            'payment_amount',
            'wallet_amount',
            'payment',
            'wallet',
            'created_by',
            'updated_by',
            'cost',
            'discount',
            'tax',
            'patient_data'
        )

    def get_cost(self, obj):
        res = InvoiceItems.objects.filter(invoice=obj.id).aggregate(
            cost=Sum('total', default=0))['cost']

        return res

    def get_discount(self, obj):
        res = InvoiceItems.objects.filter(invoice=obj.id).aggregate(
            discount=Sum('discount', default=0))['discount']
        return res

    def get_tax(self, obj):
        res = InvoiceItems.objects.filter(invoice=obj.id).aggregate(
            tax=Sum('tax_amount', default=0))['tax']
        return res

    def get_items(self, obj):
        res = InvoiceItems.objects.filter(invoice=obj.id)
        return InvoiceItemsSerializer(res, many=True).data

    def get_procedure_names(self, obj):
        res = ", ".join(list(InvoiceItems.objects.filter(invoice=obj.id).prefetch_related(
            'procedure').values_list(
            'procedure__name', flat=True)))
        return res

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} " \
               f"{obj.patient.last_name}"  #

        # res = appointment.objects.filter(invoice=obj.id)
        # return InvoiceItemsSerializer(res, many=True).data

    def get_payment(self, obj):
        res = Payment.objects.filter(invoice=obj.id)
        return PaymentSerializer(res, many=True).data

    def get_payment_amount(self, obj):
        res = Payment.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('price', default=0))['paid']
        return res

    def get_wallet_amount(self, obj):
        res = Wallet.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('amount', default=0))['paid']
        return res

    def get_wallet(self, obj):
        res = Wallet.objects.filter(invoice=obj.id)
        return WalletSerializer(res, many=True).data

    def get_due_amount(self, obj):
        paid = Payment.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('price', default=0))['paid']

        return obj.grand_total - paid if obj.grand_total - paid > 0 else 0

    def get_paid_amount(self, obj):
        paid = Payment.objects.filter(invoice=obj.id).aggregate(
            paid=Sum('price', default=0))['paid']
        return paid

    def get_advance_amount(self, obj):
        paid_amount = self.get_paid_amount(obj)
        return paid_amount - obj.grand_total if paid_amount > obj.grand_total else 0


class InvoiceItemsSerializer(serializers.ModelSerializer):
    procedure_name = serializers.SerializerMethodField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = InvoiceItems
        fields = (
            'id',
            'invoice',
            'procedure',
            'doctor',
            'procedure_name',
            'tax_amount',
            'tax_info',
            'tax_percentage',
            'quantity',
            'price',
            'total',
            'discount',
            'total_after_discount',
            'created_by',
            'updated_by'

        )

    def get_procedure_name(self, obj):
        res = Procedure.objects.get(id=obj.procedure_id)
        return res.name


class PaymentSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    invoice_number = serializers.StringRelatedField(source='invoice.invoice_number')
    invoice_date = serializers.StringRelatedField(source='invoice.date')
    procedure_names = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField(read_only=True)
    patient_atlas_id = serializers.StringRelatedField(source='patient.atlas_id')
    clinic_name = serializers.StringRelatedField(source='clinic.name')
    is_advance = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            'id',
            'patient',
            'patient_name',
            'invoice',
            'procedure_names',
            'invoice_number',
            'invoice_date',
            'type',
            'mode',
            'is_advance',
            'transaction_id',
            'transaction_type',
            'collected_on',
            'patient_atlas_id',
            'balance',
            'excess_amount',
            'receipt_id',
            'pay_notes',
            'price',
            'clinic',
            'clinic_name',
            'payment_status',
            'created_by',
            'created_at',
            'updated_by'
        )

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_procedure_names(self, obj):
        if obj.invoice:
            res = ", ".join(list(InvoiceItems.objects.filter(invoice=obj.invoice.id).prefetch_related(
                'procedure').values_list(
                'procedure__name', flat=True)))
            return res
        return ''

    def get_is_advance(self, obj):
        return 'Yes' if (not obj.invoice) or (obj.price - obj.invoice.grand_total > 0) else 'No'


class WalletSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Wallet
        fields = (
            'id',
            'user',
            'amount',
            'type',
            'invoice',
            'desc',
            'created_at',
            'created_by',
            'updated_by'
        )


class WalletPaymentSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = WalletPayment
        fields = (
            'id',
            'wallet',
            'payment',
            'contribution_amount',
            'created_at',
            'created_by',
            'updated_by'
        )


class BillingSerializer(serializers.Serializer):
    data = serializers.SerializerMethodField()
    data_type = serializers.SerializerMethodField()

    def get_data(self, obj):
        if obj.__class__.__name__ == 'Invoice':
            invoice_data = InvoiceSerializer(obj).data
            return invoice_data
        if obj.__class__.__name__ == 'Payment':
            payment_data = PaymentSerializer(obj).data
            return payment_data
        return None

    def get_data_type(self, obj):
        return str(obj.__class__.__name__).lower()

class RefundSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    payment_transaction_id = serializers.SerializerMethodField()
    invoice_number = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = '__all__'

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_payment_transaction_id(self, obj):
        return obj.payment.transaction_id

    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number if obj.invoice else None

    def create(self, validated_data):
        return Refund.objects.create(**validated_data)