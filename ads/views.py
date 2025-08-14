from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.shortcuts import get_object_or_404
import json

from ads.serializers import AdSerializer, PaymentVerificationSerializer, PaymentInitiationSerializer
from ads.models import Ad, Payment
from shop.models import Shop
from .paystack_utils import initialize_transaction, verify_transaction


class AdDetailView(generics.RetrieveAPIView):
    queryset = Ad.objects.select_related('shop', 'shop__owner')
    serializer_class = AdSerializer
    permission_classes = [IsAuthenticated]



class InitiatePaymentView(generics.CreateAPIView):
    serializer_class = PaymentInitiationSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentInitiationSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        shop_id = serializer.validated_data['shop_id']
        
        try:
            shop = Shop.objects.get(id=shop_id, owner=request.user)
        except Shop.DoesNotExist:
            return Response(
                {"error": "Shop not found or you don't have permission"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            metadata = {
                "shop_id": str(shop.id),
                "user_id": str(request.user.id)
            }
            
            paystack_response = initialize_transaction(
                email=request.user.email, 
                amount=settings.AD_PAYMENT_AMOUNT,
                metadata=metadata
            )
            
            if not paystack_response.get('status'):
                return Response(
                    {"error": "Failed to initialize payment", "details": paystack_response.get('message')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = paystack_response.get('data', {})
            authorization_url = data.get('authorization_url')
            access_code = data.get('access_code')
            reference = data.get('reference')
            
            payment = Payment.objects.create(
                shop=shop,
                amount=settings.AD_PAYMENT_AMOUNT,
                owner=request.user,
                reference=reference,
                authorization_url=authorization_url,
                access_code=access_code,
                payment_status=Payment.PENDING,
                ad=None  
            )
            
            return Response({
                "message": "Payment initialized",
                "payment_id": str(payment.id),  
                "authorization_url": authorization_url,
                "reference": reference
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": "Payment initialization failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class VerifyPaymentView(generics.CreateAPIView):
    serializer_class = PaymentVerificationSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reference = serializer.validated_data.get('reference')
        
        try:
            payment = get_object_or_404(Payment, reference=reference, owner=request.user)
            
            if payment.verified:
                return Response({
                    "message": "Payment already verified",
                    "payment_status": payment.payment_status
                })
            
            verification = verify_transaction(reference)
            
            if not verification.get('status'):
                return Response({
                    "error": "Verification failed",
                    "details": verification.get('message')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = verification.get('data', {})
            if data.get('status') == 'success':
                payment.payment_status = Payment.SUCCESS
                payment.verified = True
                payment.save()
                
                ad = Ad.objects.create(
                    shop=payment.shop,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=30),
                    is_active=True
                )
                
                payment.ad = ad
                payment.save()
                
                return Response({
                    "message": "Payment verified successfully",
                    "ad_id": ad.id,
                    "payment_status": payment.payment_status
                })
            else:
                payment.payment_status = Payment.FAILED
                payment.save()
                return Response({
                    "message": "Payment failed or pending",
                    "payment_status": payment.payment_status
                })
                
        except Exception as e:
            return Response({
                "error": "Verification process failed",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaystackWebhookView(APIView):
    """Handle Paystack webhook events"""
    
    def post(self, request):
        paystack_signature = request.headers.get('X-Paystack-Signature')
        if not paystack_signature:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        payload = request.body
        
        try:
            event = json.loads(payload)
            
            if event.get('event') == 'charge.success':
                data = event.get('data', {})
                reference = data.get('reference')
                
                try:
                    payment = Payment.objects.get(reference=reference)
                    
                    if payment.verified:
                        return Response(status=status.HTTP_200_OK)
                    
                    payment.payment_status = Payment.SUCCESS
                    payment.verified = True
                    payment.save()
                    
                    ad = Ad.objects.create(
                        shop=payment.shop,
                        start_date=timezone.now(),
                        end_date=timezone.now() + timedelta(days=30),
                        is_active=True
                    )
                    
                    payment.ad = ad
                    payment.save()
                    
                except Payment.DoesNotExist:
                    pass
            
            return Response(status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)