from django.urls import path, include

from .views import PaymentList, PaymentView, \
    CollectPayment, InvoiceList, InvoiceView, InvoiceItemsList, \
    InvoiceItemsView, CollectDuePayment, \
    SendInvoiceEmailView, GenerateInvoicePDFView, WalletBalanceView, \
    BillingView, AdvanceBalanceView, InvoiceAll, \
    PaymentStatusView, RefundList, InvoiceRefund, WalletRefund, \
    PaymentCallbackView, RazorpayWebhookView, \
    CreatePayment

# , WalletList, WalletView,

collectpayment = [
    path('', CollectPayment.as_view(), name="collect_payment"),
    path('<int:pk>/', CollectPayment.as_view(), name="update_payment"),
    path('due/', CollectDuePayment.as_view(), name="collect_due_payment"),
    path('due/<int:pk>/', CollectDuePayment.as_view(),
         name="update_due_payment"),
]

invoice = [
    path('', InvoiceList.as_view(), name='invoiceList'),
    # path('all/', InvoiceAll.as_view(), name='invoiceAll'),
    # path('download-invoice-report/',
    #      InvoiceAll.as_view({'get': 'download_invoice_report'}),
    #      name='download_invoice_report'),

    path('all/', InvoiceAll.as_view({'get': 'list'}), name='invoiceAll'),
    # Assuming 'list' is the method to list all invoices
    path('download-invoice-report/', InvoiceAll.as_view({'get': 'download_invoice_report'}),
         name='download_invoice_report'),

    path('<int:pk>/', include([
        path('', InvoiceView.as_view(), name='invoiceView'),
        path('sendmail/', SendInvoiceEmailView.as_view(),
             name='send_invoice_email'),
        path('download/', GenerateInvoicePDFView.as_view(),
             name='generate_invoice_pdf'),
    ])),
    path('items/', InvoiceItemsList.as_view(),
         name='invoice_items_list'),
    path('items/<int:pk>/', InvoiceItemsView.as_view(),
         name='invoiceitemsView')

]

wallet = [
    # path('', WalletList.as_view(), name='walletList'),
    # path('<int:pk>/', WalletView.as_view(), name='walletView'),
    path('balance/<int:user_id>/', WalletBalanceView.as_view(),
         name='wallet_balance'),
    path('advance/<int:user_id>/', AdvanceBalanceView.as_view(),
         name='advance_balance'),
]

payment = [
    path('', PaymentList.as_view(), name='paymentList'),
    path('<int:pk>/', PaymentView.as_view(), name='paymentView'),
    path('create/', CreatePayment.as_view(), name='create-payment'),
    path('status/', PaymentStatusView.as_view(), name='payment-status'),
    path('callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    # path('payment_link/', create_phonepe_payment_link, name='get_access_token'),
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]

refund = [
    path('', RefundList.as_view(), name='refundList'),
    path('invoice/', InvoiceRefund.as_view(), name='invoice-refund'),
    path('wallet/', WalletRefund.as_view(), name='wallet-refund')
]

payment_urls = [
    path('invoice/', include(invoice)),
    path('payment/', include(payment)),
    path('wallet/', include(wallet)),
    path('refund/', include(refund)),
    path('collectpayment/', include(collectpayment)),
    path('billing/', BillingView.as_view({'get': 'list'}), name='billing')
]
