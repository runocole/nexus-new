from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from authentication.models import User, PasswordResetToken
from shop.models import Shop
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from phonenumber_field.serializerfields import PhoneNumberField

class EmailUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer to allow login with either username or email
    """
    username_field = 'username_or_email'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields.pop('username', None)
        
    def validate(self, attrs):
        username_or_email = attrs.get(self.username_field)
        password = attrs.get('password')
        
        user = None
        if '@' in username_or_email:
            user = User.objects.filter(email__iexact=username_or_email).first()
        else:
            user = User.objects.filter(username__exact=username_or_email).first()
            
        if user and user.check_password(password):
            refresh = self.get_token(user)
            
            return {
                "id": str(user.id),
                "username": user.username,
                "token": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }
        else:
            raise serializers.ValidationError("Invalid username/email or password")
    
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        return {
            "id": str(self.user.id),
            "username": self.user.username,
            "token": {
                "access": data["access"],
                "refresh": data["refresh"],
            },
        }
    
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    phone_number = PhoneNumberField(required=True)
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'password', 'last_seen']
        read_only_fields = ['id', 'last_seen']
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists() and not self.instance:
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower() 
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists() and not self.instance:
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists() and not self.instance:
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
    
class ShopInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'category', 'image_url']

class UserProfileSerializer(UserSerializer):
    shops = ShopInfoSerializer(many=True, read_only=True)
    
    class Meta(UserSerializer.Meta):
        fields = ['id', 'username', 'email', 'phone_number', 'last_seen', 'shops']
        
        
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not check_password(value, user.password):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data["new_password"])
        instance.save()
        return instance
    
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("No user found with this email address")
        return value.lower()


class PasswordResetVerifySerializer(serializers.Serializer):
    token = serializers.CharField()
    
    def validate_token(self, value):
        token_obj = PasswordResetToken.objects.filter(token=value).first()
        if not token_obj:
            raise serializers.ValidationError("Invalid token")
        
        if not token_obj.is_valid():
            if token_obj.used:
                raise serializers.ValidationError("Token has already been used")
            else:
                raise serializers.ValidationError("Token has expired")
        
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    
    def validate_token(self, value):
        token_obj = PasswordResetToken.objects.filter(token=value).first()
        if not token_obj:
            raise serializers.ValidationError("Invalid token")
        
        if not token_obj.is_valid():
            if token_obj.used:
                raise serializers.ValidationError("Token has already been used")
            else:
                raise serializers.ValidationError("Token has expired")
        
        return value
    
    def validate_new_password(self, value):
        try:
            validate_password(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        
        return value