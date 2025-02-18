import datetime

from django.db import models

from appointment.models import Appointment, Procedure
from clinic.models import Clinic
from user.models import User


# Create your models here.

class Invoice(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE,
                                    null=True, blank=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='invoice_patient', null=True,
                                blank=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE,
                               related_name='invoice_clinic', null=True,
                               blank=True)
    invoice_number = models.CharField(max_length=20)
    date = models.DateField(default=datetime.date.today)
    grand_total = models.FloatField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='invoice_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='invoice_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} - INV: {self.invoice_number}"


class InvoiceItems(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    procedure = models.ForeignKey(Procedure, on_delete=models.DO_NOTHING)
    doctor = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='invoice_item_doctor', null=True,
                               blank=True, default=None)
    tax_amount = models.FloatField(null=True, blank=True)
    # {name:cess, percentate: 10% , cost: 150}
    tax_percentage = models.FloatField(null=True, blank=True)
    tax_info = models.JSONField(null=True, blank=True)
    quantity = models.IntegerField(null=True, default=1)
    price = models.FloatField(null=True, blank=True)
    total = models.FloatField(null=True, blank=True)
    discount = models.FloatField(null=True, blank=True)
    total_after_discount = models.FloatField(null=True, blank=True)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='invoice_item_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        related_name='invoice_item_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.procedure} - {self.quantity}"


MODE = (
    ('online', "Online"),
    ('offline', "Offline")
)

TYPE = (
    ('card', "Card"),
    ('cash', "Cash"),
    ('upi', "Upi"),
    ('netbanking', "Net Banking"),
    ('wallet', "Wallet")
)

PAYMENT_STATUS = (
    ('pending', 'Pending'),
    ('success', 'Success'),
    ('failed', 'Failed')
)

TRANSACTION_TYPE = (
    ('collected', 'Collected'),
    ('paid', 'Paid'),
    ('wallet_payment', 'Wallet'),
)


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True,
                                blank=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, null=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, null=True,
                                related_name='payment_patient')
    receipt_id = models.CharField(max_length=30, null=True, blank=True)
    type = models.CharField(choices=TYPE, max_length=10)
    mode = models.CharField(choices=MODE, max_length=10)
    transaction_id = models.CharField(max_length=30)
    price = models.FloatField(null=True, blank=True)
    balance = models.FloatField(default=0)
    excess_amount = models.FloatField(default=0)
    transaction_type = models.CharField(choices=TRANSACTION_TYPE,
                                        default='collected', max_length=20)
    payment_status = models.CharField(choices=PAYMENT_STATUS,
                                      default='pending', max_length=15)
    status = models.BooleanField(default=1)
    collected_on = models.DateField(null=True, blank=True)
    pay_notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='payment_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='payment_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.price}"


TRANSACTION_TYPE = (
    ('dr', 'Debit'),  # cash added to your account
    ('cr', 'Credit')  # cash paid from account
)


class Wallet(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='wallet_user')
    amount = models.FloatField(null=True, blank=True)
    type = models.CharField(choices=TRANSACTION_TYPE)
    invoice = models.ForeignKey(Invoice, null=True,
                                on_delete=models.CASCADE, blank=True)
    desc = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=1)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='wallet_created_by')
    updated_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name='wallet_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type} - {self.amount}"


class WalletPayment(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='wallet_payment_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='wallet_payment_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.wallet} - {self.payment} - {self.contribution_amount}"

class Refund(models.Model):
    REFUND_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'), 
        ('rejected', 'Rejected'),
        ('completed', 'Completed')
    )

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='refunds', null=True, blank=True)
    amount = models.FloatField()
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    reason = models.TextField(null=True, blank=True)
    refund_date = models.DateField(null=True, blank=True)
    transaction_id = models.CharField(max_length=30, unique=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refunds')
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='refund_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='refund_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund {self.transaction_id} - {self.amount}"