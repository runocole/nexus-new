from django.db import models
from cloudinary.models import CloudinaryField
from authentication.models import User
from phonenumber_field.modelfields import PhoneNumberField
from django.core.cache import cache
from math import radians, sin, cos, sqrt, atan2
from .validators import validate_image_file_extension, validate_file_size
import uuid

from django.core import validators
from django.db import models
from cloudinary.models import CloudinaryField
from authentication.models import User
from phonenumber_field.modelfields import PhoneNumberField
from math import radians, sin, cos, sqrt, atan2
from geopy.geocoders import Nominatim
import uuid
from django.core import validators
from .validators import validate_image_file_extension, validate_file_size


class Shop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops', null=True, blank=True)
    name = models.CharField(max_length=50)
    image = CloudinaryField('image', blank=True, null=True)
    description = models.TextField()
    image_url = models.CharField(max_length=250, blank=True, null=True)
    category = models.CharField(max_length=50)
    address = models.TextField()
    phone_number = PhoneNumberField(blank=True, null=True)
    visit_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, 
        blank=True, null=True,
        help_text="Latitude of the shop location"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, 
        blank=True, null=True,
        help_text="Longitude of the shop location"
    )

    class Meta:
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['owner']),
            models.Index(fields=['visit_count']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

    def distance_from(self, lat, lon):
        """
        Haversine formula to calculate distance in KM between given point and shop.
        """
        lat1, lon1, lat2, lon2 = map(radians, [
            float(lat), float(lon),
            float(self.latitude), float(self.longitude)
        ])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        km = 6371 * c
        return round(km, 2)

    def geocode_address(self):
        """
        Geocode the address into latitude and longitude using Nominatim.
        """
        if self.address and (self.latitude is None or self.longitude is None):
            geolocator = Nominatim(user_agent="shop_locator")
            location = geolocator.geocode(self.address)
            if location:
                self.latitude = location.latitude
                self.longitude = location.longitude

    def save(self, *args, **kwargs):
        # Automatically fetch coordinates if missing
        self.geocode_address()
        super().save(*args, **kwargs)

    # def visitor_count(self):
    #     cache_key = f'shop_visitor_count:{self.id}'
    #     print("🚀 ~ cache_key:", cache_key)
        
    #     if count is None:
    #         auth_count = self.shopvisit_set.count()
            
    #         anon_count_key = f'anon_visit_count:{self.id}'
    #         anon_count = cache.get(anon_count_key, 0)
            
    #         count = auth_count + anon_count
    #         cache.set(cache_key, count, 60*60) # Cache for an hour
    #     return count


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    image = CloudinaryField(
        'image', 
        blank=True, 
        null=True,
        validators=[validate_image_file_extension, validate_file_size]
    )
    price = models.PositiveIntegerField()
    image_url = models.CharField(max_length=250, blank=True, null=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="products", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True) 
    
    class Meta:
        indexes = [
            models.Index(fields=['shop']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at', '-id']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.image:
            first_save_kwargs = kwargs.copy()
            super().save(*args, **first_save_kwargs)
            
            self.image_url = self.image.url
            
            second_save_kwargs = kwargs.copy()
            if 'force_insert' in second_save_kwargs:
                del second_save_kwargs['force_insert']
                
            second_save_kwargs['update_fields'] = ['image_url']
                
            super().save(*args, **second_save_kwargs)
        else:
            super().save(*args, **kwargs)

class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='shop_reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[
            validators.MinValueValidator(1, message="Rating must be at least 1"),
            validators.MaxValueValidator(5, message="Rating cannot exceed 5")
        ]
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('shop', 'user')
        indexes = [
            models.Index(fields=['shop']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.shop.name} - {self.rating}★"