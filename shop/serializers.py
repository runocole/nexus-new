from rest_framework import serializers
from .models import Review, Shop, Product
from ads.models import Ad
from authentication.serializers import UserSerializer
from django.utils import timezone
from django.db.models import Avg


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description',  'price', 'image', 'image_url', 'shop']
        read_only_fields = ['image_url']


class ProductCreateSerializer(serializers.ModelSerializer):
    shop_id = serializers.UUIDField(write_only=True, help_text="ID of the shop this product belongs to")
    description = serializers.CharField(required=False, allow_blank=True)
    
    image = serializers.ImageField(
        required=False,
        help_text="Product image file (jpg, jpeg, png, gif, webp, max 5MB)"
    )
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'image', 'shop_id']
        read_only_fields = ['id']
    
    def validate_shop_id(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
            
        try:
            Shop.objects.get(id=value, owner=request.user)
        except Shop.DoesNotExist:
            raise serializers.ValidationError("Shop not found or you don't have permission")
            
        return value
    
    def create(self, validated_data):
        shop_id = validated_data.pop('shop_id')
        shop = Shop.objects.get(id=shop_id)
        
        product = Product.objects.create(shop=shop, **validated_data)
            
        return product


class ProductUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.IntegerField(required=False)
    image = serializers.ImageField(required=False)
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'image']
        read_only_fields = ['id']
    
    def update(self, instance, validated_data):
        
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.price = validated_data.get('price', instance.price)
        
        if 'image' in validated_data:
            instance.image = validated_data.get('image')
            
        instance.save()
            
        return instance
    
    # def save(self, *args, **kwargs):
    #     if self.image and not self.image_url:
    #         super().save(*args, **kwargs) 
    #         self.image_url = self.image.url
    #         kwargs['update_fields'] = kwargs.get('update_fields', None) or ['image_url']
    #         super().save(*args, **kwargs)
    #     else:
    #         super().save(*args, **kwargs)

class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = ['id', 'start_date', 'end_date', 'is_active']


class ShopSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    products_list = serializers.JSONField(write_only=True, required=False)
    
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    
    image = serializers.ImageField(
        required=False,
        help_text="Shop image file (jpg, jpeg, png, gif, webp, max 5MB)"
    )
    
    owner = UserSerializer(read_only=True)
    owner_phone = serializers.SerializerMethodField(read_only=True)
    distance=serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'image', 'image_url', 'description', 'category', 
            'address', 'owner', 'owner_phone', 'products', 'products_list',
            'distance'
        ]
        read_only_fields = ['image_url', 'owner', 'owner_phone', 'distance']
        
    
    def get_owner_phone(self, obj):
        if obj.owner and obj.owner.phone_number:
            return str(obj.owner.phone_number)
        return None
    
    def get_distance(self, obj):
        request = self.context.get('request')
        lat = getattr(request, "latitude", None)
        lon = getattr(request, "longitude", None)

        if lat and lon:
                return round(obj.distance_from(lat, lon), 2)
                return None
           
        
    def validate(self, data):
        if self.instance is None:
            required_fields = ['name', 'description', 'category', 'address']
            for field in required_fields:
                if field not in data:
                    raise serializers.ValidationError(f"{field} is required when creating a shop")
        return data
    

class ShopListSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    owner_phone = serializers.SerializerMethodField(read_only=True)
    visitor_count = serializers.IntegerField(read_only=True)
    owner_status = serializers.CharField(read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'image_url', 'description', 'category', 
            'address', 'owner', 'owner_phone', 'visitor_count', 
            'owner_status', 'avg_rating', 'review_count'
        ]
    
    def get_owner_phone(self, obj):
        if obj.owner and obj.owner.phone_number:
            return str(obj.owner.phone_number)
        return None
    
    def get_avg_rating(self, obj):
        if hasattr(obj, 'avg_rating') and obj.avg_rating is not None:
            return round(obj.avg_rating, 1)
        return None
    
    def get_review_count(self, obj):
        if hasattr(obj, 'review_count'):
            return obj.review_count
        return 0

class ShopDetailSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    owner = UserSerializer(read_only=True)
    owner_phone = serializers.SerializerMethodField(read_only=True)
    active_ads = serializers.SerializerMethodField()
    visitor_count = serializers.IntegerField(read_only=True)
    owner_status = serializers.CharField(read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    reviews = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'image_url', 'description', 'category', 
            'address', 'owner', 'owner_phone', 'products', 
            'visitor_count', 'owner_status', 'active_ads',
            'avg_rating', 'review_count', 'reviews'
        ]
    
    def get_owner_phone(self, obj):
        if obj.owner and obj.owner.phone_number:
            return str(obj.owner.phone_number)
        return None
    
    def get_active_ads(self, obj):
        ads = Ad.objects.filter(
            shop=obj,
            is_active=True,
            end_date__gt=timezone.now()
        )
        return AdSerializer(ads, many=True).data
    
    def get_avg_rating(self, obj):
        avg = obj.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else None

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_reviews(self, obj):
        reviews = obj.reviews.select_related('user').order_by('-created_at')[:5]
        return ReviewSerializer(reviews, many=True).data
    

class ReviewSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'shop', 'user', 'rating', 'comment', 'created_at', 'updated_at', 'user_username', 'shop_name']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'user_username', 'shop_name']

class ReviewCreateSerializer(serializers.ModelSerializer):
    shop_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'shop_id', 'rating', 'comment']
        read_only_fields = ['id']
    
    def validate_shop_id(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
            
        try:
            Shop.objects.get(id=value)
        except Shop.DoesNotExist:
            raise serializers.ValidationError("Shop not found")
            
        if Review.objects.filter(shop_id=value, user=request.user).exists():
            raise serializers.ValidationError("You have already reviewed this shop")
            
        return value
    
    def create(self, validated_data):
        shop_id = validated_data.pop('shop_id')
        shop = Shop.objects.get(id=shop_id)
        user = self.context['request'].user
        
        review = Review.objects.create(shop=shop, user=user, **validated_data)
        return review

class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rating', 'comment']