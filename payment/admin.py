from django.contrib import admin

# Register your models here.
from .models import Invoice, Payment, InvoiceItems, Wallet, WalletPayment, Refund


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'invoice_number', 'date', 'is_paid',
                    'grand_total')
    search_fields = ('id', 'invoice_number', 'date', 'patient__first_name', 'patient__last_name', 'patient__email',
                     'patient__atlas_id', 'invoice_number')
    list_filter = ('clinic', 'date', 'is_paid')
    autocomplete_fields = ('appointment', 'patient', 'created_by', 'updated_by')
    # date_hierarchy = ('date',)


@admin.register(InvoiceItems)
class InvoiceItemsAdmin(admin.ModelAdmin):
    list_display = ('id', 'price', 'total', 'total_after_discount',
                    'quantity', 'invoice')
    search_fields = ('id', 'invoice', 'quantity', 'total')
    list_filter = ('procedure', 'invoice__clinic', 'invoice__date', 'invoice__is_paid')
    autocomplete_fields = ('created_by', 'updated_by', 'invoice')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'patient', 'transaction_id', 'invoice', 'price', 'excess_amount', 'payment_status', 'transaction_type',
        'collected_on', 'type')
    search_fields = ('transaction_id', 'type', 'mode', 'id', 'patient__first_name', 'patient__last_name',
                     'patient__email', 'patient__atlas_id')
    list_filter = ('type', 'mode', 'transaction_type', 'payment_status', 'clinic', 'collected_on')
    autocomplete_fields = ('created_by', 'patient', 'updated_by', 'invoice')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amount', 'invoice', 'user', 'created_at')
    search_fields = ('id', 'type', 'amount', 'user__first_name', 'user__last_name', 'user__email', 'user__atlas_id')
    list_filter = ('type',)
    autocomplete_fields = ('user', 'created_by', 'updated_by')


@admin.register(WalletPayment)
class WalletPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'payment', 'contribution_amount', 'created_at')
    search_fields = (
        'id', 'wallet__user__first_name', 'wallet__user__last_name', 'wallet__user__email', 'wallet__user__atlas_id')
    autocomplete_fields = ('wallet', 'payment', 'created_by', 'updated_by')

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_id', 'payment', 'invoice', 'amount', 'status', 'refund_date')
    search_fields = ('transaction_id', 'payment__transaction_id', 'invoice__invoice_number')
    list_filter = ('status', 'refund_date', 'clinic')
    autocomplete_fields = ('payment', 'invoice', 'clinic', 'patient', 'created_by', 'updated_by')