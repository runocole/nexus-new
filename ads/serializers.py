from rest_framework import serializers
from .models import Ad, Payment

class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = ['id', 'shop', 'start_date', 'end_date', 'is_active', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'shop', 'amount', 'owner', 'created_at', 'reference', 'authorization_url', 'payment_status']
        read_only_fields = ['reference', 'authorization_url', 'payment_status', 'amount']


class PaymentVerificationSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=10, allow_blank=False)
    
    class Meta:
        fields = ['reference']
        
        
        
from rest_framework import serializers
from .models import Ad, Payment
from shop.models import Shop

class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = ['id', 'shop', 'start_date', 'end_date', 'is_active', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'shop', 'amount', 'owner', 'created_at', 'reference', 'authorization_url', 'payment_status']
        read_only_fields = ['reference', 'authorization_url', 'payment_status', 'amount']


class PaymentVerificationSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)


class PaymentInitiationSerializer(serializers.Serializer):
    shop_id = serializers.UUIDField()
    
    def validate_shop_id(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
            
        try:
            Shop.objects.get(id=value, owner=request.user)
        except Shop.DoesNotExist:
            raise serializers.ValidationError("Shop not found or you don't have permission")
            
        return value