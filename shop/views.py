import json
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
from django.db.models import Case, When, Value, CharField, Q, Prefetch, F
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import F
import math
import random

from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count
from drf_yasg.utils import swagger_auto_schema
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.extra.rate_limiter import RateLimiter
from .models import Shop
from .serializers import ShopListSerializer


from shop.models import Review, Shop, Product
from shop.serializers import (
    ReviewCreateSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
    ShopListSerializer,
    ShopSerializer, 
    ShopDetailSerializer,
    ProductSerializer, 
    ProductCreateSerializer, 
    ProductUpdateSerializer
)
from ads.models import Ad

class ShopView(generics.ListCreateAPIView):
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'category']
    ordering_fields = ['name', 'visitor_count']
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ShopListSerializer
        return ShopSerializer
    
    def get_queryset(self):
        queryset = Shop.objects.select_related('owner').prefetch_related(
            Prefetch('reviews', queryset=Review.objects.select_related('user')),
            Prefetch('ads', queryset=Ad.objects.filter(is_active=True, end_date__gt=timezone.now()))
        ).annotate(
            visitor_count=F('visit_count'),
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
            owner_status=Case(
                When(
                    Q(owner__last_seen__gte=timezone.now() - timedelta(minutes=5)),
                    then=Value('Online')
                ),
                default=Value('Offline'),
                output_field=CharField()
            )
        ).order_by('-created_at')
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
            
        return queryset
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        sponsored_shops = []
        for_you_shops = []
        
        for shop in queryset:
            if shop.ads.exists():
                sponsored_shops.append(shop)
            else:
                for_you_shops.append(shop)
        
        sponsored_serializer = self.get_serializer(sponsored_shops, many=True)
        for_you_serializer = self.get_serializer(for_you_shops, many=True)
        
        return Response({
            "sponsored_shops": sponsored_serializer.data,
            "for_you": for_you_serializer.data
        })
        
    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        products_list = serializer.validated_data.pop("products_list", {})
        name = serializer.validated_data.get("name")
        image = serializer.validated_data.get("image")
        description = serializer.validated_data.get("description")
        category = serializer.validated_data.get("category")
        address = serializer.validated_data.get("address")
        phone_number = serializer.validated_data.get("phone_number")
        cloudinary_url = f"https://res.cloudinary.com/dtqiuzflg/"
    
        shop = Shop.objects.create(
            name=name, 
            image=image, 
            description=description, 
            category=category, 
            address=address,
            phone_number=phone_number,
            owner=request.user
        )
        shop.image_url = f"{cloudinary_url}{shop.image}"
        shop.save(update_fields=["image_url"])

        images = request.FILES.getlist('images')
        products = products_list.get("products", [])

        if len(images) < len(products):
            return Response({"error": "Not enough images uploaded for the products."}, status=status.HTTP_400_BAD_REQUEST)
        
        product_objects = [
            Product(name=product["name"], price=product["price"], image=images[i], shop=shop)
            for i, product in enumerate(products)
        ]
        
        with transaction.atomic():
            created_products = Product.objects.bulk_create(product_objects)
             
        for product in created_products:
            product.image_url = f"{cloudinary_url}{product.image}" 
            product.save(update_fields=["image_url"]) 

        shop_data = ShopSerializer(shop).data
        response_data = {
            "shop": shop_data,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class ShopDetailView(generics.RetrieveAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopDetailSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Shop.objects.select_related('owner').prefetch_related(
            Prefetch('products', queryset=Product.objects.all().order_by('-created_at', '-id')),
            Prefetch('reviews', queryset=Review.objects.select_related('user').order_by('-created_at')),
            Prefetch('ads', queryset=Ad.objects.filter(
                is_active=True,
                end_date__gt=timezone.now()
            ))
        ).annotate(
            visitor_count=F('visit_count'),
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'), 
            owner_status=Case(
                When(
                    Q(owner__last_seen__gte=timezone.now() - timedelta(minutes=5)),
                    then=Value('Online')
                ),
                default=Value('Offline'),
                output_field=CharField()
            )
        )
        
    def get(self, request, *args, **kwargs):
        shop = self.get_object()
        
        shop.visit_count = F('visit_count') + 1
        shop.save(update_fields=['visit_count'])
        
        return super().get(request, *args, **kwargs)
        
class ShopUpdateView(generics.UpdateAPIView):
    """Update an existing shop (requires ownership)"""
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        obj = super().get_object()
        if obj.owner != self.request.user:
            raise PermissionDenied("You don't have permission to modify this shop")
        return obj
    
    def perform_update(self, serializer):
        shop = self.get_object()
        validated_data = serializer.validated_data
        
        if 'image' in validated_data and validated_data['image']:
            serializer.save()
            shop.refresh_from_db()
            shop.image_url = shop.image.url
            shop.save(update_fields=["image_url"])
        else:
            serializer.save()
            
        return Response(ShopSerializer(shop).data)


class ShopDeleteView(generics.DestroyAPIView):
    """Delete a shop (requires ownership)"""
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        obj = super().get_object()
        if obj.owner != self.request.user:
            raise PermissionDenied("You don't have permission to delete this shop")
        return obj
    
    def perform_destroy(self, instance):
        instance.delete()
        return Response({"message": "Shop deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class AllProductsListView(generics.ListAPIView):
    """List all products across all shops with filtering"""
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['shop']
    ordering_fields = ['name', 'price', 'id']
    
    def get_queryset(self):
        queryset = Product.objects.all().select_related('shop').order_by('-created_at')
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(shop__category=category)
            
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
            
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        return queryset

class ProductListView(generics.ListAPIView):
    """List all products in a shop"""
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        shop_id = self.kwargs.get('shop_id')
        return Product.objects.filter(shop_id=shop_id).order_by('-created_at')


class ProductDetailView(generics.RetrieveAPIView):
    """Retrieve a specific product"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


class ProductCreateView(generics.CreateAPIView):
    """Create a new product (requires authentication)"""
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    @swagger_auto_schema(
        operation_description="Create a new product with optional image upload",
        request_body=ProductCreateSerializer,
        responses={
            201: ProductSerializer,
            400: 'Bad Request'
        }
    )
    
    def post(self, request, *args, **kwargs):
        print(f"Request data: {request.data}")
        print(f"Request FILES: {request.FILES}")
        
        return self.create(request, *args, **kwargs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    def perform_create(self, serializer):
        """
        This method is called when saving the serializer.
        """
        try:
            serializer.save()
        except Exception as e:
            print(f"Error in perform_create: {str(e)}")
            raise
    


class ProductUpdateView(generics.UpdateAPIView):
    """Update an existing product (requires ownership)"""
    queryset = Product.objects.all()
    serializer_class = ProductUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def get_object(self):
        obj = super().get_object()
        if obj.shop.owner != self.request.user:
            raise PermissionDenied("You don't have permission to modify this product")
        return obj


class ProductDeleteView(generics.DestroyAPIView):
    """Delete a product (requires ownership)"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        obj = super().get_object()
        if obj.shop.owner != self.request.user:
            raise PermissionDenied("You don't have permission to delete this product")
        return obj


class BatchProductCreateView(APIView):
    """Create multiple products at once"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, shop_id):
        try:
            shop = Shop.objects.get(id=shop_id, owner=request.user)
        except Shop.DoesNotExist:
            return Response(
                {"error": "Shop not found or you don't have permission"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        products_data = request.data.get('products', [])
        if isinstance(products_data, str):
            try:
                products_data = json.loads(products_data)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid products data format"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        images = request.FILES.getlist('images')
        
        if len(images) < len(products_data):
            return Response(
                {"error": "Not enough images uploaded for the products."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        created_products = []
        
        with transaction.atomic():
            for i, product_data in enumerate(products_data):
                product = Product(
                    name=product_data.get('name'),
                    price=product_data.get('price'),
                    shop=shop
                )
                
                if i < len(images):
                    product.image = images[i]
                
                product.save()
                
                if product.image:
                    product.image_url = product.image.url
                    product.save(update_fields=["image_url"])
                
                created_products.append(product)
        
        serializer = ProductSerializer(created_products, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class ShopReviewsListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        shop_id = self.kwargs.get('shop_id')
        return Review.objects.filter(shop_id=shop_id).select_related('user', 'shop')


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class ReviewDetailView(generics.RetrieveAPIView):
    queryset = Review.objects.all().select_related('user', 'shop')
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]


class ReviewUpdateView(generics.UpdateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied("You don't have permission to edit this review")
        return obj


class ShopListView(generics.ListAPIView):
    serializer_class = ShopSerializer

    def get_queryset(self):
        queryset = Shop.objects.all()

        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius_km = float(self.request.query_params.get('radius', 10))  # default 10 km

        # If coordinates are provided, calculate distances
        if lat and lng:
            try:
                lat = float(lat)
                lng = float(lng)

                def haversine(lat1, lon1, lat2, lon2):
                    R = 6371  # Earth radius in km
                    phi1, phi2 = math.radians(lat1), math.radians(lat2)
                    d_phi = math.radians(lat2 - lat1)
                    d_lambda = math.radians(lon2 - lon1)
                    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
                    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

                # Annotate each shop with distance
                queryset = [
                    (shop, haversine(lat, lng, shop.latitude, shop.longitude))
                    for shop in queryset
                ]

                # Filter by radius
                queryset = [(shop, dist) for shop, dist in queryset if dist <= radius_km]

                # Sort by distance
                queryset.sort(key=lambda x: x[1])

                # Add randomness in the top few results
                top_chunk = queryset[:5]  # first 5 closest shops
                random.shuffle(top_chunk)
                queryset = top_chunk + queryset[5:]

                # Replace queryset with just shop objects but keep distances in a dict
                self.distances = {shop.id: dist for shop, dist in queryset}
                queryset = [shop for shop, _ in queryset]

            except ValueError:
                self.distances = {}
                queryset = list(queryset)
        else:
            # No location provided → just randomize
            queryset = list(queryset)
            random.shuffle(queryset)
            self.distances = {}

        return queryset

    def list(self, request, *args, **kwargs):
        # Override to inject distance into serialized data
        response = super().list(request, *args, **kwargs)
        for item in response.data:
            item['distance_km'] = round(self.distances.get(item['id'], None), 2) if self.distances else None
        return response

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from rest_framework.views import APIView
from rest_framework.response import Response
from shop.models import Shop
import random
from datetime import datetime

class NearbyShopsView(APIView):
    def post(self, request):
        address = request.data.get("address")
        if not address:
            return Response({"error": "Address is required"}, status=400)

        # Step 1: Geocode address
        geolocator = Nominatim(user_agent="lily_shop")
        location = geolocator.geocode(address, timeout=10)

        if not location:
            return Response({"error": "Could not geocode the given address"}, status=400)

        user_coords = (location.latitude, location.longitude)

        # Step 2: Find shops + calculate distance
        shops_with_distance = []
        for shop in Shop.objects.all():
            if shop.latitude and shop.longitude:
                shop_coords = (shop.latitude, shop.longitude)
                dist_km = geodesic(user_coords, shop_coords).km
                shops_with_distance.append({
                    "id": str(shop.id),
                    "name": shop.name,
                    "image": shop.image.url if shop.image else None,
                    "description": shop.description,
                    "category": shop.category,
                    "address": shop.address,
                    "owner": shop.owner.id if shop.owner else None,
                    "owner_phone": shop.owner.phone if shop.owner and hasattr(shop.owner, "phone") else None,
                    "products": [],  # You can fill in product data if needed
                    "distance": round(dist_km, 2),
                    "created_at": shop.created_at  # assuming Shop has created_at
                })

        if not shops_with_distance:
            return Response([])

        # Step 3: Algorithmic scoring
        max_distance = max([s["distance"] for s in shops_with_distance]) or 1

        def get_shop_score(shop):
            # Distance score: closer shops rank higher
            distance_score = max(0, (max_distance - shop["distance"]) / max_distance) * 0.6

            # Recency score: newer shops (less than 30 days old) rank higher
            days_since_added = (datetime.now().date() - shop["created_at"].date()).days
            recency_score = max(0, (30 - days_since_added) / 30) * 0.3

            # Random score: small shuffle so results rotate
            random_score = random.uniform(0, 0.1)

            return distance_score + recency_score + random_score

        # Add scores and sort
        shops_with_distance.sort(key=lambda x: get_shop_score(x), reverse=True)

        return Response(shops_with_distance)


class ReviewDeleteView(generics.DestroyAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied("You don't have permission to delete this review")
        return obj

class UserReviewsListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).select_related('shop')
    
import random
from datetime import datetime

def get_shop_score(shop, max_distance):
    # Base score: closer shops score higher
    distance_score = max(0, (max_distance - (shop.distance or 0)) / max_distance) * 0.6
    
    # Recency score: boost for shops < 30 days old
    days_since_added = (datetime.now().date() - shop.created_at.date()).days
    recency_score = max(0, (30 - days_since_added) / 30) * 0.3
    
    # Random factor for variation
    random_score = random.uniform(0, 0.1)
    
    return distance_score + recency_score + random_score
