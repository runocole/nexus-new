from django.urls import path
from .views import (
    AdDetailView, 
    InitiatePaymentView,
    VerifyPaymentView,
    PaystackWebhookView
)

urlpatterns = [
    path('<uuid:pk>/', AdDetailView.as_view(), name='ad-detail'),
    path('payment/initiate/', InitiatePaymentView.as_view(), name='payment-initiate'),
    path('payment/verify/', VerifyPaymentView.as_view(), name='payment-verify'),
    path('payment/webhook/', PaystackWebhookView.as_view(), name='payment-webhook'),
]